from pydantic import BaseModel
from typing import List
# Modelos para los Tours
class Tour(BaseModel):
    nombre: str
    destino: list
    descripcion: str
    duracion: str
    precio: float