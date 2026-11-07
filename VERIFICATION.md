# Verification

- Mixed-case protected-directory fixtures passed on Linux and native Windows; no real credentials were used. This is not a full platform or publication audit.

- Native Windows Python 3.14 ran a synthetic paired toy-duel comparison with identical configurations. The Packet Storm adapter was not run on Windows.
- Earlier Linux tests exercised synthetic fixtures and an isolated copy of the real Packet Storm simulation with identical and changed tunings. The stationary-bot scenario is not human gameplay or a general balance judgment.
- Broader gameplay, Windows simulation build, a reviewed demo and the complete publication audit remain unverified.
- 2026-11-07: real-input trial through Hermes's tool registry in a disposable profile. balance_compare_duel ran 2,000 paired seeded duels and returned win rates 0.795 versus 0.8855 with a paired standard error of 0.0064 (a toy model, not a real game). balance_packet_storm compiled an isolated copy of the user's real Packet Storm game simulation offline and ran 3 trials per tuning file of 30 simulated seconds each (candidate: firewall max_speed 420 to 300) in 16 s wall time; it returned per-trial rows. No claim is made about which tuning is better. The tool's 55 s build-plus-run deadline is tight for a cold Rust build.
- 2026-11-07: `balance_packet_storm` takes an optional `time_limit_seconds` (10 to 900, default 55) for the offline Cargo build plus runs, because the old fixed 55 s limit is tight for a cold build of a larger game. Validation is tested; 8 tests pass.
