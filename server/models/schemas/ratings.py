from pydantic import BaseModel


class RatingCreate(BaseModel):
    rating: int
