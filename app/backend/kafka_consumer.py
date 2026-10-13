import json
import time
import os
from kafka import KafkaConsumer
from api_client import analyze_sentiment, TemporaryAIError
from mongodb import MongoDBConnection
from config import MONGODB_URI, MONGODB_DATABASE

# Initialize MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", MONGODB_URI)
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
mongo_conn = MongoDBConnection(MONGO_URI, MONGODB_DATABASE)
db = mongo_conn.get_database()

def main():
    # Configurando o consumer para o tópico 'feedback' com auto commit desabilitado
    consumer = KafkaConsumer(
        'feedback',
        bootstrap_servers=[KAFKA_BROKER],
        auto_offset_reset='earliest',
        enable_auto_commit=False,
        group_id='feedback_process',
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )

    print("Kafka Consumer iniciado e escutando o tópico 'feedback'...")

    # Loop infinito para processamento contínuo das mensagens
    for message in consumer:
        try:
            # A mensagem já foi convertida para dict pelo deserializer
            msg_dict = message.value
            print(f"Mensagem recebida: partição={message.partition}, offset={message.offset}")

            response = analyze_sentiment(msg_dict['comment'], msg_dict['rating'])

            response_dict = {
                "comment": msg_dict["comment"],
                "rating": msg_dict["rating"]
            }

            response_dict.update(response)
            
            # Save response to MongoDB
            feedback_collection = db["feedback"]
            feedback_collection.insert_one(response_dict)
            print(f"Feedback salvo no MongoDB: offset={message.offset}")

            # Commit manual após processar a mensagem
            consumer.commit()
        except Exception as e:
            print(f"Erro ao processar a mensagem: {e}")
            consumer.close(autocommit=False)
            raise

        time.sleep(0.1)  # Pequena pausa para evitar loop intenso

if __name__ == '__main__':
    while True:
        try:
            main()
            break
        except TemporaryAIError:
            print("IA indisponível. Mensagem não confirmada; retomando em 60 segundos.", flush=True)
            time.sleep(60)
