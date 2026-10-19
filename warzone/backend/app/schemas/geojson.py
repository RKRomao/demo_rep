from pydantic import BaseModel, Field
from typing import List, Dict, Any, Union, Optional

class GeoJSONGeometry(BaseModel):
    type: str = Field(..., example="Point")
    coordinates: Union[List[float], List[List[float]], List[List[List[float]]]]

class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    id: Optional[Union[int, str]] = None
    geometry: GeoJSONGeometry
    properties: Dict[str, Any] = {}

class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature] = []
