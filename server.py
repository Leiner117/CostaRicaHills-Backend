import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, HTTPException, File, Form
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from models import Tour
from supabase import create_client, Client
from typing import List
# Cargar variables de entorno
load_dotenv()
# Supabase 
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configurar CORS
origins = [
    "http://localhost:5173",  # Añade aquí los orígenes permitidos
    "https://costaricahills-backend.onrender.com",
]

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

if not firebase_admin._apps:
    cred = credentials.Certificate(credenciales_json)
    firebase_admin.initialize_app(cred)

# Inicializar Firestore
db = firestore.client()

# Crear la aplicación FastAPI
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# ---- Add Methods ----
@app.post("/tours")
async def add_tour(
    nombre: str = Form(...),
    descripcion: str = Form(...),
    canton: str = Form(...),
    provincia: str = Form(...),
    duracion: str = Form(...),
    precio: float = Form(...),
    imagenes: List[UploadFile] = File(...)
):
    try:
        destino = [canton, provincia]
        tour = Tour(
            nombre=nombre,
            descripcion=descripcion,
            destino=destino,
            duracion=duracion,
            precio=precio
        )
        doc_ref = db.collection('tours').document()
        doc_ref.set(tour.dict())
        for imagen in imagenes:
            uploadFile("tours", imagen, nombre)
        return tour.dict()
    except Exception as e:
        return {"error": str(e)}

@app.get("/tours/{tour_id}")
async def get_tour(tour_id: str):
    try:
        doc_ref = db.collection('tours').document(tour_id)
        doc = doc_ref.get()
        if doc.exists:
            tour_data = doc.to_dict()
            tour_name = tour_data["nombre"]
            bucket_name = "CostaRicaHillsBucket" 
            tour_data["imagenes"] = get_file(bucket_name, tour_name)
            return tour_data
        else:
            return {"error": "Tour not found"}
    except Exception as e:
        return {"error": str(e)}

# ---- Update Methods ----
@app.put("/tours/{tour_id}")
async def update_tour(
    tour_id: str,
    nombre: str = Form(None),
    descripcion: str = Form(None),
    canton: str = Form(None),
    provincia: str = Form(None),
    duracion: str = Form(None),
    precio: float = Form(None),
    imagenes: List[UploadFile] = File(None)
):
    try:
        doc_ref = db.collection('tours').document(tour_id)
        doc = doc_ref.get()
        if doc.exists:
            tour = Tour(**doc.to_dict())
            if nombre:
                tour.nombre = nombre
            if descripcion:
                tour.descripcion = descripcion
            if canton:
                tour.destino[0] = canton
            if provincia:
                tour.destino[1] = provincia
            if duracion:
                tour.duracion = duracion
            if precio:
                tour.precio = precio
            doc_ref.set(tour.dict())
            return tour.dict()
        else:
            return {"error": "Tour not found"}
    except Exception as e:
        return {"error": str(e)}

# ---- Delete Methods ----
@app.delete("/tours/{tour_id}")
async def delete_tour(tour_id: str):
    try:
        doc_ref = db.collection('tours').document(tour_id)
        doc = doc_ref.get()
        if doc.exists:
            doc_ref.delete()
            delete_all_files("tours", doc.to_dict()["nombre"])
            return {"message": "Tour deleted"}
        else:
            return {"error": "Tour not found"}
    except Exception as e:
        return {"error": str(e)} 
#--- find tour by name ---
@app.get("/toursByName/{tour_name}")
async def get_tour_by_name(tour_name: str):
    try:
        tours = db.collection('tours').stream()
        for tour in tours:
            if tour.to_dict()["nombre"] == tour_name:
                
                return {"id": tour.id}
        return {"error": "Tour not found"}
    except Exception as e:
        return {"error": str(e)}
@app.get("/toursAll")
async def get_all_tours():
    try:
        tours = db.collection('tours').stream()
        tour_list = []
        bucket_name = "CostaRicaHillsBucket" 
        for tour in tours:
            tour_data = tour.to_dict()
            tour_data['id'] = tour.id
            tour_name = tour_data["nombre"]
            tour_data["imagenes"] = get_file(bucket_name, tour_name)
            tour_list.append(tour_data)
        
        return tour_list
    except Exception as e:
        return {"error": str(e)}

def uploadFile(bucket_name: str, file: UploadFile, tourName: str):
    response = None
    file_content = file.file.read()
    file_path = f"{tourName}/{file.filename}"
    response = supabase.storage.from_("CostaRicaHillsBucket").upload(file_path, file_content)
    return {"mensaje": "Archivo subido exitosamente", "detalles": response}
# ---- upload file ----
@app.post("/uploadFile/")
async def upload_file(
    bucket_name: str = Form(...),
    tourName: str = Form(...),
    files: List[UploadFile] = File(...)
):
    try:
        responses = []
        for file in files:
            file_content = await file.read()
            file_path = f"{tourName}/{file.filename}"
            response = supabase.storage.from_(bucket_name).upload(file_path, file_content)
            responses.append(response)
        return {"mensaje": "Archivos subidos exitosamente", "detalles": responses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir los archivos: {str(e)}")
# ---- get files ----
@app.get("/getFiles/")
def get_file(bucket_name: str, tourName: str):
    try:
        response = supabase.storage.from_(bucket_name).list(tourName+"/")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener el bucket: {str(e)}")
    link_list = []
    for i in response:
        link = supabase.storage.from_(bucket_name).get_public_url(tourName+"/"+i["name"])
        link_list.append(link)
    return link_list

#--- delete all files---
def delete_all_files(bucket_name: str, tourName: str):
    try:
        response = supabase.storage.from_(bucket_name).remove([tourName+"/"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar el bucket: {str(e)}")
    return {"mensaje": "Archivos eliminados exitosamente", "detalles": response}
#--- delete file ---
@app.delete("/deleteFile/")
def delete_file(bucket_name: str, tourName: str, fileName: str):
    try:
        url = tourName+"/"+fileName[:-1]
        response = supabase.storage.from_(bucket_name).remove([url])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar el archivo: {str(e)}")
    return {"mensaje": "Archivo eliminado exitosamente", "detalles": response}
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="localhost", port=port)
#--- add reserve ---
@app.post("/Addreserves")
#params: tour_id, user_id, date, cant_persons
async def add_reserve(
    tour_id: str = Form(...),
    user_id: str = Form(...),
    startDate: str = Form(...),
    endDate: str = Form(...),
    cant_persons: int = Form(...),
    status: str = Form(...)

):
    try:
        reserve = {
            "tour_id": tour_id,
            "user_id": user_id,
            "startDate": startDate,
            "EndDate": endDate,
            "cant_persons": cant_persons,
            "status": status
        }
        doc_ref = db.collection('toursReservas').document()
        doc_ref.set(reserve)
        return reserve
    except Exception as e:
        return {"error": str(e)}
#--- get reserves ---
@app.get("/getReserves")
async def get_reserves():
    try:
        reserves = db.collection('toursReservas').stream()
        reserve_list = []
        for reserve in reserves:
            reserve_data = reserve.to_dict()
            reserve_data['id'] = reserve.id
            reserve_list.append(reserve_data)
        return reserve_list
    except Exception as e:
        return {"error": str(e)}
#--- get reserves by user ---
@app.get("/getReservesByUser/{user_id}")
async def get_reserves_by_user(user_id: str):
    try:
        reserves = db.collection('toursReservas').stream()
        reserve_list = []
        for reserve in reserves:
            reserve_data = reserve.to_dict()
            if reserve_data["user_id"] == user_id:
                reserve_data['id'] = reserve.id
                reserve_list.append(reserve_data)
        return reserve_list
    except Exception as e:
        return {"error": str(e)}
#--- get reserves by tour ---
@app.get("/getReservesByTour/{tour_id}")
async def get_reserves_by_tour(tour_id: str):
    try:
        reserves = db.collection('toursReservas').stream()
        reserve_list = []
        for reserve in reserves:
            reserve_data = reserve.to_dict()
            if reserve_data["tour_id"] == tour_id:
                reserve_data['id'] = reserve.id
                reserve_list.append(reserve_data)
        return reserve_list
    except Exception as e:
        return {"error": str(e)}
#--- delete reserve ---
@app.delete("/deleteReserve/{reserve_id}")
async def delete_reserve(reserve_id: str):
    try:
        doc_ref = db.collection('toursReservas').document(reserve_id)
        doc = doc_ref.get()
        if doc.exists:
            doc_ref.delete()
            return {"message": "Reserve deleted"}
        else:
            return {"error": "Reserve not found"}
    except Exception as e:
        return {"error": str(e)}
