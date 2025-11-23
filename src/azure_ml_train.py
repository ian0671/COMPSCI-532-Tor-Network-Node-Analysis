"""
Azure ML Training Script for Threat Intelligence Models
Integrates with Azure ML Workspace for scalable model training
"""

import argparse
import os
import pandas as pd
import joblib
from azureml.core import Run, Dataset, Workspace
from azureml.core.model import Model
from ml_threat_detection import ThreatIntelligenceML

def main():
    """Main training function for Azure ML"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-folder', type=str, dest='data_folder', help='data folder mounting point')
    parser.add_argument('--output-folder', type=str, dest='output_folder', help='output folder')
    args = parser.parse_args()

    # Get Azure ML run context
    run = Run.get_context()
    
    try:
        # Initialize ML pipeline
        ml_pipeline = ThreatIntelligenceML()
        
        # Load threat intelligence data from flattened parquet files
        print("Loading threat intelligence data from flattened storage...")
        abuseipdb_data = ml_pipeline.load_abuseipdb_data()
        censys_data = ml_pipeline.load_censys_data()
        tor_data = ml_pipeline.load_tor_data()
        
        # Log data metrics
        run.log("abuseipdb_records", len(abuseipdb_data))
        run.log("censys_records", len(censys_data))
        run.log("tor_records", len(tor_data))
        
        # Create features
        print("Creating threat detection features...")
        threat_data = ml_pipeline.create_threat_features(abuseipdb_data, tor_data)
        run.log("total_features", len(threat_data))
        
        # Train threat detection model
        print("Training threat detection model...")
        threat_model = ml_pipeline.train_threat_detection_model(threat_data)
        
        if threat_model:
            accuracy = threat_model.score(
                ml_pipeline.scaler.transform(threat_data[['abuseConfidencePercentage', 'is_tor_relay', 'high_abuse_score', 'suspicious_port']].fillna(0)),
                ml_pipeline.encoders['threat_level'].transform(threat_data['threat_level'])
            )
            run.log("threat_model_accuracy", accuracy)
            print(f"Threat Detection Accuracy: {accuracy:.3f}")
        
        # Train anomaly detection model
        print("Training anomaly detection model...")
        anomaly_model = ml_pipeline.train_anomaly_detection_model(threat_data)
        
        # Save models to Azure ML
        os.makedirs('outputs', exist_ok=True)
        
        if 'threat_detection' in ml_pipeline.models:
            joblib.dump(ml_pipeline.models['threat_detection'], 'outputs/threat_detection_model.pkl')
            print("Saved threat detection model")
        
        if 'anomaly_detection' in ml_pipeline.models:
            joblib.dump(ml_pipeline.models['anomaly_detection'], 'outputs/anomaly_detection_model.pkl')
            print("Saved anomaly detection model")
        
        # Save preprocessing objects
        joblib.dump(ml_pipeline.scaler, 'outputs/scaler.pkl')
        joblib.dump(ml_pipeline.encoders, 'outputs/encoders.pkl')
        
        print("Azure ML training completed successfully!")
        
    except Exception as e:
        print(f"Error during training: {e}")
        run.log("training_error", str(e))
        raise

if __name__ == '__main__':
    main()