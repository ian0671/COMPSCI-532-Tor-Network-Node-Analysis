"""
Deploy Threat Intelligence Models to Azure ML
"""

from azureml.core import Workspace, Environment, ScriptRunConfig, Experiment
from azureml.core.compute import ComputeTarget, AmlCompute
from azureml.core.compute_target import ComputeTargetException

def deploy_to_azure_ml():
    """Deploy threat intelligence models to Azure ML workspace"""
    
    try:
        # Connect to Azure ML workspace
        ws = Workspace.from_config()
        print(f"Connected to workspace: {ws.name}")
        
        # Create compute target
        compute_name = "threat-intel-compute"
        try:
            compute_target = ComputeTarget(workspace=ws, name=compute_name)
            print(f"Using existing compute target: {compute_name}")
        except ComputeTargetException:
            print(f"Creating new compute target: {compute_name}")
            compute_config = AmlCompute.provisioning_configuration(
                vm_size="STANDARD_D2_V2",
                max_nodes=2,
                min_nodes=0,
                idle_seconds_before_scaledown=300
            )
            compute_target = ComputeTarget.create(ws, compute_name, compute_config)
            compute_target.wait_for_completion(show_output=True)
        
        # Create environment
        env = Environment.from_pip_requirements(
            name="threat-intel-env",
            file_path="../ml-requirements.txt"
        )
        
        # Create experiment
        experiment = Experiment(workspace=ws, name="threat-intelligence-training")
        
        # Configure training script
        src = ScriptRunConfig(
            source_directory="../src",
            script="azure_ml_train.py",
            compute_target=compute_target,
            environment=env
        )
        
        # Submit training job
        run = experiment.submit(config=src)
        print(f"Training job submitted. Run ID: {run.id}")
        print(f"Monitor at: {run.get_portal_url()}")
        
        return run
        
    except Exception as e:
        print(f"Error deploying to Azure ML: {e}")
        return None

if __name__ == "__main__":
    run = deploy_to_azure_ml()
    if run:
        print("Deployment successful!")
    else:
        print("Deployment failed!")