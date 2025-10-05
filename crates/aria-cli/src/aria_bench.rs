//! aria-bench - Performance benchmarks

use aria_domain::*;
use aria_telemetry::*;
use clap::Parser;
use std::time::Instant;

#[derive(Parser, Debug)]
#[command(name = "aria-bench")]
#[command(about = "Run ARIA SDK benchmarks", long_about = None)]
struct Args {
    /// Benchmark to run (codec, compression, fec, crypto, e2e)
    #[arg(short, long, default_value = "all")]
    bench: String,
    
    /// Number of iterations
    #[arg(short = 'n', long, default_value = "1000")]
    iterations: usize,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();
    
    let args = Args::parse();
    
    println!("ARIA SDK Benchmarks");
    println!("===================\n");
    
    if args.bench == "all" || args.bench == "compression" {
        bench_compression(args.iterations);
    }
    
    if args.bench == "all" || args.bench == "fec" {
        bench_fec(args.iterations);
    }
    
    if args.bench == "all" || args.bench == "crypto" {
        bench_crypto(args.iterations);
    }
    
    Ok(())
}

fn bench_compression(iterations: usize) {
    println!("Compression Benchmark (LZ4):");
    let compressor = Lz4Compressor::new(1);
    let data = vec![0u8; 4096];
    
    let start = Instant::now();
    for _ in 0..iterations {
        let _ = compressor.compress(&data).unwrap();
    }
    let elapsed = start.elapsed();
    
    println!("  {} iterations in {:?}", iterations, elapsed);
    println!("  {:.2} µs/op", elapsed.as_micros() as f64 / iterations as f64);
    println!();
}

fn bench_fec(iterations: usize) {
    println!("FEC Benchmark (Reed-Solomon):");
    let fec = ReedSolomonFec;
    let data = vec![0u8; 1024];
    let k = 4;
    let m = 2;
    
    let start = Instant::now();
    for _ in 0..iterations {
        let _ = fec.encode(&data, k, m).unwrap();
    }
    let elapsed = start.elapsed();
    
    println!("  {} iterations in {:?}", iterations, elapsed);
    println!("  {:.2} µs/op", elapsed.as_micros() as f64 / iterations as f64);
    println!();
}

fn bench_crypto(iterations: usize) {
    println!("Crypto Benchmark (Ed25519 + ChaCha20-Poly1305):");
    let crypto = CryptoBox::new("bench-key".into());
    let data = vec![0u8; 1024];
    let nonce = [0u8; 12];
    
    let start = Instant::now();
    for _ in 0..iterations {
        let signature = crypto.sign(&data).unwrap();
        let _ = crypto.verify(&data, &signature).unwrap();
        let _ = crypto.encrypt(&data, &nonce).unwrap();
    }
    let elapsed = start.elapsed();
    
    println!("  {} iterations in {:?}", iterations, elapsed);
    println!("  {:.2} µs/op", elapsed.as_micros() as f64 / iterations as f64);
    println!();
}
