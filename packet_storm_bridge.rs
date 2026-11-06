//! Compiled only inside an isolated user-supplied Packet Storm source copy.
//! A stationary bot chooses the first offered card; this is not a human playtest.
use glam::Vec2;
use packet_storm_sim::{Sim, Tuning};

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 5 { std::process::exit(2); }
    let text = std::fs::read_to_string(&args[1]).expect("read tuning");
    let tuning = Tuning::from_ron(&text).expect("parse tuning");
    let start: u64 = args[2].parse().expect("seed");
    let count: u64 = args[3].parse().expect("count");
    let seconds: f64 = args[4].parse().expect("duration");
    if !tuning.tick_hz.is_finite() || !(1.0..=240.0).contains(&tuning.tick_hz)
        || tuning.pool_capacity == 0 || tuning.pool_capacity > 50_000 {
        eprintln!("Unsupported simulation tick rate or pool capacity");
        std::process::exit(2);
    }
    let max_ticks = (seconds * tuning.tick_hz).ceil() as usize + 1;
    for seed in start..start + count {
        let mut sim = Sim::new(tuning.clone(), seed);
        let mut steps = 0usize;
        while !sim.is_over() && sim.stats.elapsed < seconds as f32 && steps < max_ticks {
            sim.set_input(Vec2::ZERO);
            sim.step();
            if sim.offer.is_some() { sim.choose(0); }
            steps += 1;
        }
        println!("{},{:.6},{},{},{}", seed, sim.stats.elapsed, sim.level, sim.stats.breaches, sim.stats.collateral);
    }
}
