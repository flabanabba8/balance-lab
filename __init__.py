import json
from .core import compare_duel
from .packet_storm import packet_storm

STATS = {'type': 'object', 'properties': {'hp': {'type': 'number', 'exclusiveMinimum': 0}, 'damage': {'type': 'number', 'exclusiveMinimum': 0}, 'hit': {'type': 'number', 'minimum': 0, 'maximum': 1}, 'crit': {'type': 'number', 'minimum': 0, 'maximum': 1}, 'crit_multiplier': {'type': 'number', 'minimum': 1, 'maximum': 10}}, 'required': ['hp', 'damage', 'hit', 'crit', 'crit_multiplier'], 'additionalProperties': False}

def invoke(name, args):
    try:
        return json.dumps((packet_storm if name == 'balance_packet_storm' else compare_duel)(**args), allow_nan=False)
    except (ValueError, TypeError, OverflowError, OSError, RuntimeError) as exc:
        return json.dumps({'error': str(exc)})

def register(ctx):
    ctx.register_tool(name='balance_compare_duel', toolset='balance_lab', schema={'name': 'balance_compare_duel',
        'description': 'Compare two configurations in the same seeded toy duel model, using paired random rolls. This is not a simulation of a particular game.',
        'parameters': {'type': 'object', 'properties': {'baseline': STATS, 'candidate': STATS, 'enemy': STATS, 'trials': {'type': 'integer', 'minimum': 2, 'maximum': 10000}, 'max_turns': {'type': 'integer', 'minimum': 1, 'maximum': 300}, 'seed': {'type': 'integer'}}, 'required': ['baseline', 'candidate', 'enemy', 'trials', 'max_turns', 'seed'], 'additionalProperties': False}},
        handler=lambda args, **kwargs: invoke('balance_compare_duel', args))
    ctx.register_tool(name='balance_packet_storm', toolset='balance_lab', schema={'name': 'balance_packet_storm',
        'description': 'Compare two user-supplied Packet Storm tuning files by compiling and running an isolated copy of the trusted game simulation. Cargo build scripts execute; no game files are intentionally modified. Offline Cargo cache required.',
        'parameters': {'type': 'object', 'properties': {'project_path': {'type': 'string'}, 'baseline_tuning': {'type': 'string'}, 'candidate_tuning': {'type': 'string'}, 'seed': {'type': 'integer', 'minimum': 1}, 'trials': {'type': 'integer', 'minimum': 1, 'maximum': 10}, 'max_seconds': {'type': 'integer', 'minimum': 1, 'maximum': 120}, 'time_limit_seconds': {'type': 'integer', 'minimum': 10, 'maximum': 900, 'description': 'Wall-clock limit for the offline Cargo build plus the runs; default 55. Raise it for a large game on a cold build cache.'}}, 'required': ['project_path', 'baseline_tuning', 'candidate_tuning', 'seed', 'trials', 'max_seconds'], 'additionalProperties': False}},
        handler=lambda args, **kwargs: invoke('balance_packet_storm', args))
