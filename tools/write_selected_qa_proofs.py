"""Validate a reviewed runtime-proof plan. Dry-run unless --write is explicit."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(plan):
    manifest = json.loads(Path(plan['manifest']).read_text(encoding='utf-8'))
    for output, proof in plan['outputs'].items():
        path = Path(output)
        path.resolve().relative_to(Path('work/ui').resolve())
        assert path.name == 'validation.en.json'
        assert proof['version'] == manifest['version']
        for key, source in [('iso_sha256', 'iso_sha256'),
                            ('executable_sha256', 'output_elf_sha256'),
                            ('archive_sha256', 'dialogue_cpk_sha256')]:
            assert proof[key] == manifest[source], key
        for capture in proof['captures']:
            assert digest(capture['path']) == capture['sha256']
            assert digest(capture['metadata']) == capture['metadata_sha256']
            metadata = json.loads(Path(capture['metadata']).read_text(encoding='utf-8'))
            assert metadata['version'] == proof['version']
            assert metadata['loaded_executable_sha256'] == proof['executable_sha256']
        assert not path.exists(), 'Fresh proof required; existing proof cannot be replaced.'
    return plan['outputs']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--expected-plan-sha256', required=True)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    assert digest(args.plan) == args.expected_plan_sha256
    outputs = validate(json.loads(args.plan.read_text(encoding='utf-8')))
    for output, proof in outputs.items():
        print(json.dumps({'output': output, 'status': proof['status'],
                          'captures': len(proof['captures']), 'write': args.write}))
    if args.write:
        # All inputs and all fresh destinations pass before any output is saved.
        for output, proof in outputs.items():
            path = Path(output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
