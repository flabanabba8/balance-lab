import importlib.util
import subprocess
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('packet_balance_core', Path(__file__).parents[1] / 'packet_storm.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

class CopyTests(unittest.TestCase):
    def test_copy_isolated_and_source_unchanged(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as temp:
            root = Path(temp)
            project, dest = root / 'project', root / 'copy'
            sim = project / 'crates' / 'sim'
            sim.mkdir(parents=True)
            dest.mkdir()
            (project/'Cargo.toml').write_text('[workspace]\nmembers = ["crates/sim", "crates/game"]\ndefault-members = ["crates/game"]\n')
            (project/'Cargo.lock').write_text('fixture')
            (sim/'Cargo.toml').write_text('[package]\nname="packet_storm_sim"\nversion="0.1.0"\n')
            (sim/'lib.rs').write_text('original')
            before = (project/'Cargo.toml').read_bytes()
            digest = core.copied_source(project, dest)
            self.assertEqual(len(digest), 64)
            self.assertEqual((project/'Cargo.toml').read_bytes(), before)
            self.assertIn('members = ["crates/sim"]', (dest/'Cargo.toml').read_text())
            (dest/'crates/sim/lib.rs').write_text('changed copy')
            self.assertEqual((sim/'lib.rs').read_text(), 'original')

    def test_private_directory_is_not_copied(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as temp:
            root = Path(temp)
            project, dest = root / 'project', root / 'copy'
            sim = project / 'crates' / 'sim'
            sim.mkdir(parents=True)
            dest.mkdir()
            (project/'Cargo.toml').write_text('[workspace]\nmembers=["crates/sim"]\n')
            (project/'Cargo.lock').write_text('fixture')
            for name in ('.CoDeX', '.GiT'):
                folder=sim/name;folder.mkdir()
                with self.assertRaisesRegex(ValueError, 'Private configuration'):
                    core.copied_source(project, dest)
                folder.rmdir()

    def test_timeout_stops_owned_process_group(self):
        process = Mock()
        process.pid = 98765
        process.poll.return_value = None
        process.stdout = None
        process.wait.side_effect = [subprocess.TimeoutExpired('fixture', 1), -9]
        with patch.object(core.subprocess, 'Popen', return_value=process), patch.object(core.os, 'killpg') as kill:
            with self.assertRaises(subprocess.TimeoutExpired):
                core.run_owned(['fixture'], '/tmp', {}, 1)
        kill.assert_called_once_with(process.pid, core.signal.SIGKILL)

    def test_symlinked_source_is_rejected(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as temp:
            root = Path(temp)
            project, dest = root / 'project', root / 'copy'
            sim = project / 'crates' / 'sim'
            sim.mkdir(parents=True)
            dest.mkdir()
            (project/'Cargo.toml').write_text('[workspace]\nmembers=["crates/sim"]\n')
            (project/'Cargo.lock').write_text('fixture')
            (sim/'link').symlink_to(root)
            with self.assertRaisesRegex(ValueError, 'Symlink'):
                core.copied_source(project, dest)

if __name__ == '__main__': unittest.main()
