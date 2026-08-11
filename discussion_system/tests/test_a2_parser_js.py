"""Browser-side A2 parser regression tests.

The transcript parser lives in the inline browser script, so execute that exact
source with Node instead of maintaining a divergent Python reimplementation.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]
HTML = ROOT / "app" / "templates" / "index.html"


def test_v4_parser_preserves_markdown_headers_long_turns_and_context():
    html = HTML.read_text(encoding="utf-8")
    start = html.index("const PERSONA_TABLE")
    end = html.index("// ---- 저장된 .md 토론을 라이브 UI 구조로 복원")
    parser_source = html[start:end]
    program = f"""
const vm = require('vm');
const context = {{ console }};
vm.createContext(context);
vm.runInContext({json.dumps(parser_source)}, context);
const first = '## 본문 안의 헤더\\n### B\\n끝부분\\n' + 'x'.repeat(9000);
const second = '둘째 발언';
const doc = [
  '# Agent Agora — 주제', '', '- 형식: 토론 (`debate`)', '',
  '## 참여 에이전트', '', '- **A** (`a0`) — model-a',
  '- **B** (`a1`) — model-b', '', '## 참고 자료', '', '근거 자료 전체', '',
  '## 의견', '', '### A', '', first, '', '### B', '', second, '',
  '> 진행자 개입 (→ A): A에게만 전달된 지시', '',
].join('\\n');
const parsed = context.parseWithExactAnchors(doc, {{ exactLengths: true,
  lens: [[...first].length, [...second].length] }});
if (!parsed) throw new Error('parseWithExactAnchors returned null');
if (parsed.phases[0].turns.length !== 2) throw new Error('turn count mismatch');
if (parsed.phases[0].turns[0].content !== first) throw new Error('embedded headers or long turn lost');
if (parsed.phases[0].turns[1].content !== second) throw new Error('second turn mismatch');
if (parsed.referenceMaterials !== '근거 자료 전체') throw new Error('reference material lost');
const iv = parsed.phases[0].interventions[0];
if (!iv || iv.target !== 'A' || iv.message !== 'A에게만 전달된 지시') throw new Error('targeted intervention lost');
"""
    result = subprocess.run(
        ["node", "-e", program], cwd=ROOT, text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stderr
