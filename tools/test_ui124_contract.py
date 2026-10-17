"""UI-only regression contract; real browser acceptance is separate."""
from pathlib import Path
import unittest
R=Path(__file__).resolve().parents[1]
class TouchContract(unittest.TestCase):
 def test_touch_has_no_persistent_highlight(self):
  css=(R/'src/style.css').read_text()
  self.assertIn('-webkit-tap-highlight-color:transparent',css)
  self.assertIn('touch-action:manipulation',css)
 def test_busy_is_exposed_to_assistive_technology(self):
  for name in ['AddTask.tsx','Settings.tsx','Detail.tsx','TorrentList.tsx']:
   self.assertIn('aria-busy={busy}',(R/'src'/name).read_text(),name)
if __name__=='__main__':unittest.main()
