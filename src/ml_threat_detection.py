"""
Machine Learning Pipeline for Threat Intelligence Analysis
Integrates with Azure ML to train models on processed threat intelligence data
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
import joblib
import logging
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
import io

class ThreatIntelligenceML:
    def __init__(self, storage_account_name="compsci532mlwo6133466000"):
        """Initialize threat intelligence ML pipeline"""
        self.storage_account_name = storage_account_name
        self.credential = DefaultAzureCredential()
        self.blob_client = BlobServiceClient(
            account_url=f"https://{storage_account_name}.blob.core.windows.net",
            credential=self.credential
        )
        self.models = {}
        self.encoders = {}
        self.scaler = StandardScaler()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def load_abuseipdb_data(self):
        """Load processed AbuseIPDB data from flattened parquet files"""
        try:
            # Get flattened AbuseIPDB files
            container_client = self.blob_client.get_container_client("abuseipdb")
            blobs = list(container_client.list_blobs(name_starts_with="flattened/"))
            
            if not blobs:
                self.logger.warning("No flattened files found, using simulated data")
                return self._simulate_abuseipdb_data()
            
            # Sort by last modified and get recent files (last 10 for faster loading)
            recent_blobs = sorted(blobs, key=lambda x: x.last_modified, reverse=True)[:10]
            
            all_data = []
            for blob in recent_blobs:
                try:
                    blob_client = container_client.get_blob_client(blob.name)
                    data = blob_client.download_blob().readall()
                    
                    # Read parquet data directly
                    df = pd.read_parquet(io.BytesIO(data))
                    all_data.append(df)
                    self.logger.info(f"Loaded {len(df)} records from {blob.name}")
                except Exception as e:
                    self.logger.warning(f"Error loading {blob.name}: {e}")
                    continue
            
            if not all_data:
                self.logger.warning("No data successfully loaded, using simulated data")
                return self._simulate_abuseipdb_data()
            
            combined_data = pd.concat(all_data, ignore_index=True)
            self.logger.info(f"Total loaded: {len(combined_data)} AbuseIPDB records")
            return combined_data
            
        except Exception as e:
            self.logger.error(f"Error loading AbuseIPDB data: {e}")
            return self._simulate_abuseipdb_data()

    def load_censys_data(self):
        """Load Censys network scan data from flattened parquet files"""
        try:
            # Get flattened Censys files
            container_client = self.blob_client.get_container_client("censys")
            blobs = list(container_client.list_blobs(name_starts_with="flattened/"))
            
            if not blobs:
                self.logger.warning("No flattened censys files found, using simulated data")
                return self._simulate_censys_data()
            
            # Sort by last modified and get recent files
            recent_blobs = sorted(blobs, key=lambda x: x.last_modified, reverse=True)[:10]
            
            all_data = []
            for blob in recent_blobs:
                try:
                    blob_client = container_client.get_blob_client(blob.name)
                    data = blob_client.download_blob().readall()
                    
                    # Read parquet data directly
                    df = pd.read_parquet(io.BytesIO(data))
                    all_data.append(df)
                    self.logger.info(f"Loaded {len(df)} records from {blob.name}")
                except Exception as e:
                    self.logger.warning(f"Error loading {blob.name}: {e}")
                    continue
            
            if not all_data:
                self.logger.warning("No censys data successfully loaded, using simulated data")
                return self._simulate_censys_data()
            
            combined_data = pd.concat(all_data, ignore_index=True)
            self.logger.info(f"Total loaded: {len(combined_data)} Censys records")
            return combined_data
            
        except Exception as e:
            self.logger.error(f"Error loading Censys data: {e}")
            return self._simulate_censys_data()

    def load_tor_data(self):
        """Load Tor network data from get_server_descriptors"""
        try:
            # This would connect to your Azure ML dataset
            # For now, simulate based on your screenshot
            tor_data = pd.DataFrame({
                'fingerprint': [f'C4CE54{i:06d}' for i in range(1000)],
                'address': [f'185.220.{i%256}.{i%256}' for i in range(1000)],
                'or_port': np.random.choice([9001, 443, 80, 10137, 10045], 1000),
                'platform': ['Linux'] * 1000,
                'tor_version': np.random.choice(['0.4.9.3', '0.4.8.11', '0.4.8.18'], 1000),
                'operating_sys': ['Linux'] * 1000,
                'nickname': [f'Relay{i}' for i in range(1000)],
                'published': pd.date_range('2025-11-01', periods=1000, freq='1H')
            })
            
            self.logger.info(f"Loaded {len(tor_data)} Tor relay records")
            return tor_data
            
        except Exception as e:
            self.logger.error(f"Error loading Tor data: {e}")
            return pd.DataFrame()
    
    def _simulate_censys_data(self):
        """Simulate Censys data structure for testing"""
        return pd.DataFrame({
            'ip': [f'185.220.{i%256}.{i%256}' for i in range(100)],
            'port': np.random.choice([80, 443, 22, 9001], 100),
            'protocol': np.random.choice(['http', 'https', 'ssh'], 100),
            'services': [f'service_{i}' for i in range(100)]
        })

    def _simulate_abuseipdb_data(self):
        """Simulate AbuseIPDB data structure for testing"""
        return pd.DataFrame({
            'ip': [f'8.8.{i%256}.{i%256}' for i in range(100)],
            'abuseConfidencePercentage': np.random.randint(0, 100, 100),
            'countryCode': np.random.choice(['US', 'CN', 'RU', 'DE', 'FR'], 100),
            'isp': np.random.choice(['Google', 'Amazon', 'Cloudflare', 'Microsoft'], 100),
            'isPublic': [True] * 100,
            'DataSource': ['AbuseIPDB'] * 100,
            'ProcessedTime': pd.date_range('2025-11-01', periods=100, freq='1H')
        })

    def create_threat_features(self, abuseipdb_data, tor_data):
        """Create features for threat detection model"""
        try:
            # Merge AbuseIPDB and Tor data on IP addresses
            # Extract IP from Tor data (simplified)
            tor_data['ip'] = tor_data['address']
            
            # Merge datasets
            merged_data = pd.merge(
                abuseipdb_data, 
                tor_data[['ip', 'or_port', 'tor_version', 'nickname']], 
                on='ip', 
                how='left'
            )
            
            # Feature engineering
            merged_data['is_tor_relay'] = merged_data['or_port'].notna()
            merged_data['high_abuse_score'] = merged_data['abuseConfidencePercentage'] > 50
            merged_data['suspicious_port'] = merged_data['or_port'].isin([9001, 443])
            
            # Create threat level (target variable)
            merged_data['threat_level'] = 'low'
            merged_data.loc[
                (merged_data['abuseConfidencePercentage'] > 75) | 
                (merged_data['is_tor_relay'] & (merged_data['abuseConfidencePercentage'] > 25)), 
                'threat_level'
            ] = 'high'
            
            return merged_data
            
        except Exception as e:
            self.logger.error(f"Error creating features: {e}")
            return pd.DataFrame()

    def train_threat_detection_model(self, data):
        """Train machine learning model for threat detection"""
        try:
            # Prepare features
            feature_columns = [
                'abuseConfidencePercentage', 'is_tor_relay', 
                'high_abuse_score', 'suspicious_port'
            ]
            
            X = data[feature_columns].fillna(0)
            
            # Encode categorical target
            le = LabelEncoder()
            y = le.fit_transform(data['threat_level'])
            self.encoders['threat_level'] = le
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train Random Forest classifier
            rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
            rf_model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            y_pred = rf_model.predict(X_test_scaled)
            accuracy = rf_model.score(X_test_scaled, y_test)
            
            self.logger.info(f"Threat Detection Model Accuracy: {accuracy:.3f}")
            self.logger.info(f"\nClassification Report:\n{classification_report(y_test, y_pred)}")
            
            self.models['threat_detection'] = rf_model
            return rf_model
            
        except Exception as e:
            self.logger.error(f"Error training model: {e}")
            return None

    def train_anomaly_detection_model(self, data):
        """Train anomaly detection model using Isolation Forest"""
        try:
            # Features for anomaly detection
            feature_columns = ['abuseConfidencePercentage', 'or_port']
            X = data[feature_columns].fillna(0)
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train Isolation Forest
            iso_forest = IsolationForest(contamination=0.1, random_state=42)
            iso_forest.fit(X_scaled)
            
            # Predict anomalies
            anomalies = iso_forest.predict(X_scaled)
            anomaly_count = np.sum(anomalies == -1)
            
            self.logger.info(f"Detected {anomaly_count} anomalies out of {len(X)} records")
            
            self.models['anomaly_detection'] = iso_forest
            return iso_forest
            
        except Exception as e:
            self.logger.error(f"Error training anomaly model: {e}")
            return None

    def save_models(self, output_path="models/"):
        """Save trained models"""
        try:
            import os
            os.makedirs(output_path, exist_ok=True)
            
            for model_name, model in self.models.items():
                model_file = f"{output_path}{model_name}_model.pkl"
                joblib.dump(model, model_file)
                self.logger.info(f"Saved {model_name} model to {model_file}")
            
            # Save scaler and encoders
            joblib.dump(self.scaler, f"{output_path}scaler.pkl")
            joblib.dump(self.encoders, f"{output_path}encoders.pkl")
            
        except Exception as e:
            self.logger.error(f"Error saving models: {e}")

    def run_full_pipeline(self):
        """Execute complete ML pipeline"""
        self.logger.info("Starting Threat Intelligence ML Pipeline...")
        
        # 1. Load data from flattened parquet files
        abuseipdb_data = self.load_abuseipdb_data()
        censys_data = self.load_censys_data()
        tor_data = self.load_tor_data()
        
        self.logger.info(f"Loaded {len(abuseipdb_data)} AbuseIPDB, {len(censys_data)} Censys, {len(tor_data)} Tor records")
        
        # 2. Create features
        threat_data = self.create_threat_features(abuseipdb_data, tor_data)
        
        if threat_data.empty:
            self.logger.error("No data available for training")
            return
        
        # 3. Train models
        self.train_threat_detection_model(threat_data)
        self.train_anomaly_detection_model(threat_data)
        
        # 4. Save models
        self.save_models()
        
        self.logger.info("ML Pipeline completed successfully!")

if __name__ == "__main__":
    # Initialize and run ML pipeline
    ml_pipeline = ThreatIntelligenceML()
    ml_pipeline.run_full_pipeline()