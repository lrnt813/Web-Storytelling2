from typing import List, Optional

from pydantic import BaseModel, Field

LEVEL_DESC = "Level intensitas banjir: baseline | rendah | sedang | tinggi"


class RoadCutItem(BaseModel):
    lat: Optional[float] = Field(None, description="Latitude WGS84")
    lng: Optional[float] = Field(None, description="Longitude WGS84")
    x: Optional[float] = Field(None, description="Koordinat X EPSG:32749")
    y: Optional[float] = Field(None, description="Koordinat Y EPSG:32749")
    edge_from: Optional[List[float]] = Field(None, description="[x,y] node asal edge")
    edge_to: Optional[List[float]] = Field(None, description="[x,y] node tujuan edge")


class SimulateRequest(BaseModel):
    level: Optional[str] = Field("baseline", description=LEVEL_DESC)
    intensity: Optional[float] = Field(None, ge=0.0, le=1.0, description="Alternatif numerik untuk level")
    cut_roads: List[RoadCutItem] = Field(default_factory=list)


class RouteAllTesRequest(BaseModel):
    lat: float = Field(..., description="Latitude asal (WGS84)")
    lng: float = Field(..., description="Longitude asal (WGS84)")
    id_grid: Optional[int] = Field(None, description="ID grid asal bila request berasal dari klik polygon grid")
    level: Optional[str] = Field("baseline", description=LEVEL_DESC)
    intensity: Optional[float] = Field(None, ge=0.0, le=1.0)
    cut_roads: List[RoadCutItem] = Field(
        default_factory=list,
        description="Daftar titik jalan yang diputus oleh user (opsional)",
    )


class RoadRequest(BaseModel):
    level: Optional[str] = "baseline"
    intensity: Optional[float] = None
    cut_roads: List[dict] = []
    full: bool = False
