"""Paired Monte Carlo for an explicitly simplified, turn-based duel model."""
import math
import random

KEYS = {'hp', 'damage', 'hit', 'crit', 'crit_multiplier'}


def validate(stats):
    if not isinstance(stats, dict) or set(stats) != KEYS:
        raise ValueError('Each fighter needs hp, damage, hit, crit and crit_multiplier')
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in stats.values()):
        raise ValueError('Statistics must be finite numbers')
    if not 0 < stats['hp'] <= 1e9 or not 0 < stats['damage'] <= 1e9 or not 0 <= stats['hit'] <= 1 or not 0 <= stats['crit'] <= 1 or not 1 <= stats['crit_multiplier'] <= 10:
        raise ValueError('Statistic outside supported bounds')


def fight(player, enemy, rolls):
    hp, enemy_hp = player['hp'], enemy['hp']
    for turn, (ph, pc, eh, ec) in enumerate(rolls, 1):
        if ph < player['hit']:
            enemy_hp -= player['damage'] * (player['crit_multiplier'] if pc < player['crit'] else 1)
        if enemy_hp <= 0:
            return 'win', turn
        if eh < enemy['hit']:
            hp -= enemy['damage'] * (enemy['crit_multiplier'] if ec < enemy['crit'] else 1)
        if hp <= 0:
            return 'loss', turn
    return 'timeout', len(rolls)


def compare_duel(baseline, candidate, enemy, trials, max_turns, seed):
    for fighter in (baseline, candidate, enemy):
        validate(fighter)
    if type(trials) is not int or not 2 <= trials <= 10000 or type(max_turns) is not int or not 1 <= max_turns <= 300 or type(seed) is not int or abs(seed) > 2**63:
        raise ValueError('Invalid trial count, turn limit or seed')
    rng = random.Random(seed)
    counts = [{'win': 0, 'loss': 0, 'timeout': 0, 'turns': 0} for _ in range(2)]
    deltas = []
    for _ in range(trials):
        rolls = [tuple(rng.random() for _ in range(4)) for _ in range(max_turns)]
        outcomes = [fight(fighter, enemy, rolls) for fighter in (baseline, candidate)]
        for count, (result, turns) in zip(counts, outcomes):
            count[result] += 1
            count['turns'] += turns
        deltas.append(int(outcomes[1][0] == 'win') - int(outcomes[0][0] == 'win'))
    mean = sum(deltas) / trials
    variance = sum((x - mean)**2 for x in deltas) / (trials - 1)
    for count in counts:
        count['win_rate'] = count['win'] / trials
        count['mean_turns'] = count.pop('turns') / trials
    return {'baseline': counts[0], 'candidate': counts[1], 'win_rate_difference': mean,
            'paired_standard_error': math.sqrt(variance / trials), 'seed': seed, 'trials': trials, 'max_turns': max_turns,
            'model': 'Player attacks first; on surviving, enemy attacks once. Independent hit and crit rolls; capped turns are timeouts.',
            'notice': 'This toy model does not reproduce a real game. Match mechanics and validate against actual game outcomes before using the estimates.'}
