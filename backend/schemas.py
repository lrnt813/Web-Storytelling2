from typing import List, Optional

from pydantic import BaseModel, Field


class RoadCutItem(BaseModel):
    lat: Optional[float] = Field(None, description="Latitude WGS84")
    lng: Optional[float] = Field(None, description="Longitude WGS84")
    x: Optional[float] = Field(None, description="Koordinat X EPSG:32749")
    y: Optional[float] = Field(None, description="Koordinat Y EPSG:32749")
    edge_from: Optional[List[float]] = Field(None, description="[x,y] node asal edge")
    edge_to: Optional[List[float]] = Field(None, description="[x,y] node tujuan edge")


class SimulateRequest(BaseModel):
    skenario: str = Field(..., description="banjir | banjir_bandang | tanah_longsor")
    intensity: float = Field(..., ge=0.0, le=1.0)
    cut_roads: List[RoadCutItem] = Field(default_factory=list)


class RouteRequest(BaseModel):
    lat: float = Field(..., description="Latitude asal (WGS84)")
    lng: float = Field(..., description="Longitude asal (WGS84)")
    skenario: str = Field("banjir")
    intensity: float = Field(0.0, ge=0.0, le=1.0)


class RouteAllTesRequest(BaseModel):
    lat: float = Field(..., description="Latitude asal (WGS84)")
    lng: float = Field(..., description="Longitude asal (WGS84)")
    id_grid: Optional[int] = Field(None, description="ID grid asal bila request berasal dari klik polygon grid")
    skenario: str = Field("banjir")
    intensity: float = Field(0.0, ge=0.0, le=1.0)
    cut_roads: List[RoadCutItem] = Field(
        default_factory=list,
        description="Daftar titik jalan yang diputus oleh user (opsional)",
    )


class RoadRequest(BaseModel):
    skenario: str = "banjir"
    intensity: float = 0.0
    cut_roads: List[dict] = []
    full: bool = False
