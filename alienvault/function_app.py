import logging
import azure.functions as func
#from VirusTotalTimer import Virus_Total_Timer
from AlienVault.AlienVaultTimer import AlienVault_OTX_Timer


app = func.FunctionApp()
#app.register_functions(Virus_Total_Timer)
app.register_functions(AlienVault_OTX_Timer)
