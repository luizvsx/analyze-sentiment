from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator
from mongodb import MongoDBConnection
from config import MONGODB_DATABASE, MONGODB_URI
from kafka_producer import KafkaFeedbackProducer
from pymongo.errors import PyMongoError
from fastapi import HTTPException
import os



MONGO_URI = os.environ.get('MONGO_URI', MONGODB_URI)
FAST_API_HOST = os.environ.get('FAST_HOST', 'localhost')

app = FastAPI()
producer = KafkaFeedbackProducer()

class Evaluation(BaseModel):
    comment: str = Field(min_length=1, max_length=5000)
    rating: int = Field(ge=1, le=5)

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O comentário não pode estar vazio.")
        return value

mongo_conn = MongoDBConnection(MONGO_URI, MONGODB_DATABASE)
db = mongo_conn.get_database()

@app.post("/feedback/")
async def feedback(evaluation: Evaluation):
    try:
        producer.produce_feedback(evaluation.model_dump())
    except RuntimeError as erro:
        raise HTTPException(
            status_code=503,
            detail="Não foi possível enviar o comentário ao Kafka.",
        ) from erro
    return {"status": "Enviado para o tópico kafka", "descricao": "Aguardando processamento"}

@app.get("/feedback/")
def list_feedback():
    try:
        documents = list(db["feedback"].find().sort("_id", -1).limit(100))
    except PyMongoError as erro:
        raise HTTPException(
            status_code=503,
            detail="Não foi possível consultar os feedbacks no MongoDB.",
        ) from erro

    for document in documents:
        document["_id"] = str(document["_id"])
    return documents


@app.get("/feedback/{comment}")
async def get_feedback(comment: str):
    try:
        feedback_collection = db["feedback"]
        feedback = feedback_collection.find_one({"comment": comment})

        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback não encontrado.")

        # Remove o campo '_id' antes de retornar a resposta
        feedback.pop("_id", None)
        return feedback

    except PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Erro ao acessar o banco de dados: {str(e)}")
