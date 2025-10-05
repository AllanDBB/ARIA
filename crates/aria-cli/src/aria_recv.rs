//! aria-recv - Subscribe and decrypt envelopes

use aria_domain::*;
use aria_telemetry::*;
use clap::Parser;

#[derive(Parser, Debug)]
#[command(name = "aria-recv")]
#[command(about = "Receive and decode telemetry envelopes", long_about = None)]
struct Args {
    /// Topic to subscribe to
    #[arg(short, long, default_value = "test")]
    topic: String,
    
    /// Decrypt messages
    #[arg(short, long)]
    decrypt: bool,
    
    /// Output format (json, text)
    #[arg(short, long, default_value = "text")]
    format: String,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();
    
    let args = Args::parse();
    
    tracing::info!("Listening on topic '{}'", args.topic);
    
    let mut transport = QuicTransport::new();
    let codec = ProtobufCodec::new();
    
    tracing::info!("aria-recv ready");
    
    // In production: set up receive handler
    // transport.on_receive(Box::new(|envelope| {
    //     println!("Received: {:?}", envelope);
    // })).await;
    
    tokio::signal::ctrl_c().await?;
    
    Ok(())
}
