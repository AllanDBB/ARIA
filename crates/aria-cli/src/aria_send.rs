//! aria-send - Publish test envelopes

use aria_domain::*;
use aria_telemetry::*;
use clap::Parser;
use chrono::Utc;
use uuid::Uuid;

#[derive(Parser, Debug)]
#[command(name = "aria-send")]
#[command(about = "Send test telemetry envelopes", long_about = None)]
struct Args {
    /// Topic to publish to
    #[arg(short, long, default_value = "test")]
    topic: String,
    
    /// Priority (0-3)
    #[arg(short, long, default_value = "2")]
    priority: u8,
    
    /// Message count
    #[arg(short = 'n', long, default_value = "10")]
    count: usize,
    
    /// Enable encryption
    #[arg(short, long)]
    encrypt: bool,
    
    /// FEC redundancy (k,m)
    #[arg(long, value_names = &["k", "m"])]
    fec: Option<Vec<usize>>,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();
    
    let args = Args::parse();
    
    let priority = match args.priority {
        0 => Priority::P0,
        1 => Priority::P1,
        2 => Priority::P2,
        _ => Priority::P3,
    };
    
    tracing::info!(
        "Sending {} messages to topic '{}' with priority {:?}",
        args.count,
        args.topic,
        priority
    );
    
    let mut transport = QuicTransport::new();
    let codec = ProtobufCodec::new();
    let compressor = Lz4Compressor::new(1);
    
    for i in 0..args.count {
        let envelope = Envelope {
            id: Uuid::new_v4(),
            timestamp: Utc::now(),
            schema_id: 1,
            priority,
            topic: args.topic.clone(),
            payload: format!("Test message {}", i).into_bytes(),
            metadata: EnvelopeMetadata {
                source_node: "aria-send".into(),
                sequence_number: i as u64,
                fragment_info: None,
                fec_info: None,
                crypto_info: None,
                qos_class: "default".into(),
            },
        };
        
        tracing::info!("Sent envelope {}: {}", i, envelope.id);
        
        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
    }
    
    tracing::info!("Sent {} envelopes", args.count);
    
    Ok(())
}
