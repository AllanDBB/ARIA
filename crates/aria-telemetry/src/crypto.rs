//! Cryptography: sign-then-encrypt (TX), verify-then-decrypt (RX)

use aria_domain::{AriaError, AriaResult, ICryptoBox};
use chacha20poly1305::{
    aead::{Aead, KeyInit, Payload},
    ChaCha20Poly1305, Nonce,
};
use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use rand::rngs::OsRng;

pub struct CryptoBox {
    signing_key: SigningKey,
    verifying_key: VerifyingKey,
    cipher: ChaCha20Poly1305,
    key_id: String,
}

impl CryptoBox {
    pub fn new(key_id: String) -> Self {
        let mut csprng = OsRng;
        let signing_key = SigningKey::generate(&mut csprng);
        let verifying_key = signing_key.verifying_key();
        
        // Generate ChaCha20-Poly1305 key
        let cipher_key = ChaCha20Poly1305::generate_key(&mut OsRng);
        let cipher = ChaCha20Poly1305::new(&cipher_key);
        
        Self {
            signing_key,
            verifying_key,
            cipher,
            key_id,
        }
    }
    
    pub fn from_keys(signing_key: SigningKey, cipher_key: &[u8; 32], key_id: String) -> Self {
        let verifying_key = signing_key.verifying_key();
        let cipher = ChaCha20Poly1305::new(cipher_key.into());
        
        Self {
            signing_key,
            verifying_key,
            cipher,
            key_id,
        }
    }
}

impl ICryptoBox for CryptoBox {
    fn sign(&self, data: &[u8]) -> AriaResult<Vec<u8>> {
        let signature = self.signing_key.sign(data);
        Ok(signature.to_bytes().to_vec())
    }
    
    fn verify(&self, data: &[u8], signature: &[u8]) -> AriaResult<bool> {
        let sig = Signature::from_slice(signature)
            .map_err(|e| AriaError::Crypto(format!("Invalid signature: {}", e)))?;
        
        Ok(self.verifying_key.verify(data, &sig).is_ok())
    }
    
    fn encrypt(&self, data: &[u8], nonce: &[u8]) -> AriaResult<Vec<u8>> {
        let nonce_arr = Nonce::from_slice(nonce);
        
        self.cipher
            .encrypt(nonce_arr, data)
            .map_err(|e| AriaError::Crypto(format!("Encryption failed: {}", e)))
    }
    
    fn decrypt(&self, ciphertext: &[u8], nonce: &[u8]) -> AriaResult<Vec<u8>> {
        let nonce_arr = Nonce::from_slice(nonce);
        
        self.cipher
            .decrypt(nonce_arr, ciphertext)
            .map_err(|e| AriaError::Crypto(format!("Decryption failed: {}", e)))
    }
    
    fn key_id(&self) -> &str {
        &self.key_id
    }
}

/// Key manager for rotation and multi-key support
pub struct KeyManager {
    active_key_id: String,
    keys: std::collections::HashMap<String, CryptoBox>,
}

impl KeyManager {
    pub fn new() -> Self {
        Self {
            active_key_id: String::new(),
            keys: std::collections::HashMap::new(),
        }
    }
    
    pub fn add_key(&mut self, key_id: String, crypto_box: CryptoBox) {
        if self.active_key_id.is_empty() {
            self.active_key_id = key_id.clone();
        }
        self.keys.insert(key_id, crypto_box);
    }
    
    pub fn get_active_key(&self) -> Option<&CryptoBox> {
        self.keys.get(&self.active_key_id)
    }
    
    pub fn get_key(&self, key_id: &str) -> Option<&CryptoBox> {
        self.keys.get(key_id)
    }
    
    pub fn rotate(&mut self, new_key_id: String) {
        if self.keys.contains_key(&new_key_id) {
            self.active_key_id = new_key_id;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_sign_verify() {
        let crypto = CryptoBox::new("test-key".into());
        let data = b"Hello, World!";
        
        let signature = crypto.sign(data).unwrap();
        assert!(crypto.verify(data, &signature).unwrap());
        
        // Wrong data should fail
        assert!(!crypto.verify(b"Wrong data", &signature).unwrap());
    }
    
    #[test]
    fn test_encrypt_decrypt() {
        let crypto = CryptoBox::new("test-key".into());
        let data = b"Secret message";
        let nonce = [0u8; 12];
        
        let ciphertext = crypto.encrypt(data, &nonce).unwrap();
        assert_ne!(ciphertext.as_slice(), data);
        
        let plaintext = crypto.decrypt(&ciphertext, &nonce).unwrap();
        assert_eq!(plaintext.as_slice(), data);
    }
    
    #[test]
    fn test_wrong_nonce_fails() {
        let crypto = CryptoBox::new("test-key".into());
        let data = b"Secret message";
        let nonce1 = [0u8; 12];
        let nonce2 = [1u8; 12];
        
        let ciphertext = crypto.encrypt(data, &nonce1).unwrap();
        let result = crypto.decrypt(&ciphertext, &nonce2);
        assert!(result.is_err());
    }
    
    #[test]
    fn test_key_manager() {
        let mut manager = KeyManager::new();
        
        let key1 = CryptoBox::new("key1".into());
        let key2 = CryptoBox::new("key2".into());
        
        manager.add_key("key1".into(), key1);
        manager.add_key("key2".into(), key2);
        
        assert!(manager.get_active_key().is_some());
        
        manager.rotate("key2".into());
        assert_eq!(manager.get_active_key().unwrap().key_id(), "key2");
    }
}
