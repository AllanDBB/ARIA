//! Sensor adapters

use aria_domain::{ISensorAdapter, AriaResult, RawSample, SensorData};
use async_trait::async_trait;
use chrono::Utc;
use nalgebra::Vector3;

pub struct MockCamera {
    sensor_id: String,
    width: u32,
    height: u32,
}

impl MockCamera {
    pub fn new(sensor_id: String, width: u32, height: u32) -> Self {
        Self { sensor_id, width, height }
    }
}

#[async_trait]
impl ISensorAdapter for MockCamera {
    async fn start(&mut self) -> AriaResult<()> {
        tracing::info!("Mock camera {} started", self.sensor_id);
        Ok(())
    }
    
    async fn stop(&mut self) -> AriaResult<()> {
        tracing::info!("Mock camera {} stopped", self.sensor_id);
        Ok(())
    }
    
    async fn read(&mut self) -> AriaResult<RawSample> {
        Ok(RawSample {
            sensor_id: self.sensor_id.clone(),
            timestamp: Utc::now(),
            data: SensorData::Image {
                width: self.width,
                height: self.height,
                channels: 3,
                data: vec![0u8; (self.width * self.height * 3) as usize],
            },
        })
    }
    
    fn sensor_id(&self) -> &str {
        &self.sensor_id
    }
}

pub struct MockImu {
    sensor_id: String,
}

impl MockImu {
    pub fn new(sensor_id: String) -> Self {
        Self { sensor_id }
    }
}

#[async_trait]
impl ISensorAdapter for MockImu {
    async fn start(&mut self) -> AriaResult<()> {
        tracing::info!("Mock IMU {} started", self.sensor_id);
        Ok(())
    }
    
    async fn stop(&mut self) -> AriaResult<()> {
        tracing::info!("Mock IMU {} stopped", self.sensor_id);
        Ok(())
    }
    
    async fn read(&mut self) -> AriaResult<RawSample> {
        Ok(RawSample {
            sensor_id: self.sensor_id.clone(),
            timestamp: Utc::now(),
            data: SensorData::Imu {
                accel: Vector3::new(0.0, 0.0, 9.81),
                gyro: Vector3::zeros(),
                mag: Some(Vector3::new(0.0, 1.0, 0.0)),
            },
        })
    }
    
    fn sensor_id(&self) -> &str {
        &self.sensor_id
    }
}
