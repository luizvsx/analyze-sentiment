import os
import json
from confluent_kafka import Producer, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic

DEFAULT_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC = "feedback"

class KafkaFeedbackProducer:
    def __init__(self, broker=DEFAULT_BROKER, topic=TOPIC):
        self.broker = broker
        self.topic = topic
        self.producer_config = {
            "bootstrap.servers": self.broker,
        }
        self.admin_config = {
            "bootstrap.servers": self.broker,
        }
        self.producer = Producer(self.producer_config)
        self.admin_client = AdminClient(self.admin_config)
        self.ensure_topic_exists()

    def delivery_report(self, err, msg):
        """Callback para reportar o resultado do envio."""
        if err is not None:
            print(f"Falha ao entregar mensagem: {err}")
        else:
            print(f"Mensagem entregue: {msg.topic()} [{msg.partition()}]")

    def ensure_topic_exists(self):
        """Verifica se o tópico existe e o cria caso não exista."""
        topics = self.admin_client.list_topics(timeout=10).topics
        if self.topic in topics:
            print(f"Tópico '{self.topic}' já existe.")
            return

        new_topic = NewTopic(self.topic, num_partitions=1, replication_factor=1)
        fs = self.admin_client.create_topics([new_topic])
        for topic, f in fs.items():
            try:
                f.result()  # aguarda a criação
                print(f"Tópico '{topic}' criado com sucesso.")
            except Exception as e:
                print(f"Falha ao criar o tópico '{topic}': {e}")

    def produce_feedback(self, feedback_data: dict):
        """Aguarda a confirmação do Kafka antes de confirmar o envio à API."""
        delivery = []

        def on_delivery(err, msg):
            delivery.append(err)

        try:
            message = json.dumps(feedback_data)
            self.producer.produce(self.topic, value=message, callback=on_delivery)
            self.producer.flush(10)
        except (KafkaException, BufferError) as erro:
            raise RuntimeError("Não foi possível enviar o comentário ao Kafka.") from erro

        if not delivery or delivery[0] is not None:
            raise RuntimeError("O Kafka não confirmou a entrega do comentário.")
