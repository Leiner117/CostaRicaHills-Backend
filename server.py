import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from models import Tour
import httpx
from supabase import create_client, Client

# Supabase 
SUPABASE_URL = "https://ivjggofdakuwpkibfodt.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml2amdnb2ZkYWt1d3BraWJmb2R0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczMTEwNTA0MiwiZXhwIjoyMDQ2NjgxMDQyfQ.nAqUxY2RIrx1NXatY4u0BYvfU7BhWWy-WebCwoNJ5ao"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
# Cargar variables de entorno
load_dotenv()

# Crear un diccionario con las credenciales
credenciales_json = {
    "type": os.getenv("FIREBASE_TYPE"),
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
    "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
    "universal_domain": os.getenv("FIREBASE_UNIVERSE_DOMAIN")
}

# Verificar si ya se ha inicializado la app
if not firebase_admin._apps:
    cred = credentials.Certificate(credenciales_json)
    firebase_admin.initialize_app(cred)

# Inicializar Firestore
db = firestore.client()

# Crear la aplicación FastAPI
app = FastAPI()

# ---- Add Methods ----
@app.post("/tours")
async def add_tour(tour: Tour):
    try:
        doc_ref = db.collection('tours').document()
        doc_ref.set(tour.dict())
        return {"message": "Tour added successfully"}
    except Exception as e:
        return {"error": str(e)}

# ---- Get Methods ----
@app.get("/tours/{tour_id}")
async def get_tour(tour_id: str):
    try:
        doc_ref = db.collection('tours').document(tour_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            return {"error": "Tour not found"}
    except Exception as e:
        return {"error": str(e)}
# ---- upload file ----
@app.post("/uploadFile/")
async def subir_archivo(bucket_name: str, file: UploadFile, tourName: str):
    try:
        response = supabase.storage.from_(bucket_name).upload(tourName+"/"+file.name, file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir el archivo: {str(e)}")
    return {"mensaje": "Archivo subido exitosamente", "detalles": response}
# ---- get files ----
@app.get("/getFiles/")
def obtener_bucket(bucket_name: str, tourName: str):
    try:
        response = supabase.storage.from_(bucket_name).list(tourName+"/")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener el bucket: {str(e)}")
    link_list = []
    for i in response:
        link = supabase.storage.from_(bucket_name).get_public_url(tourName+"/"+i["name"])
        link_list.append(link)
    return link_list

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="localhost", port=port)
