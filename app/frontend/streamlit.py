import streamlit as st
import requests
import os

# Obter o nome do host do FastAPI a partir da variável de ambiente
# ou usar 'fastapi' como padrão
fastapi_host = os.getenv('FASTAPI_HOST', 'fastapi')


def submit_comment(comment, rating):
    try:
        feedback_list = requests.post(
            f"http://{fastapi_host}:8000/feedback/",
            json={"comment": comment, "rating": rating},
            timeout=90
        )

        # Verifica se a API retornou algum erro
        if not feedback_list.ok:
            try:
                mensagem = feedback_list.json().get(
                    "detail",
                    "Erro desconhecido."
                )
            except ValueError:
                mensagem = "O servidor retornou uma resposta inválida."

            st.error(f"Erro ao analisar comentário: {mensagem}")
            return

        # Converte a resposta para JSON
        feedback = feedback_list.json()

        if isinstance(feedback, dict) and feedback.get("status") in (
            "pendente", "Enviado para o tópico kafka"
        ):
            st.success("Comentário enviado para processamento.")
            st.info("Após o consumer processar, clique em Atualizar lista na aba Feedbacks salvos.")
            return

        # Verifica se os campos esperados existem
        if not isinstance(feedback, dict) or not all(
            campo in feedback
            for campo in ("descricao", "status")
        ):
            st.error("A API retornou uma resposta inesperada.")
            return

        # Mantém a exibição original
        status_color = (
            "green" if feedback['status'] == 'aprovado' else "red"
        )

        st.write(f"**Você comentou:** {comment}")
        st.write(f"**Avaliação:** {rating} estrelas")
        st.write(f"**Feedback:** {feedback['descricao']}")
        st.markdown(
            f"**Status:** **<span style='color:{status_color}'>"
            f"{feedback['status']}</span>**",
            unsafe_allow_html=True
        )

    except requests.exceptions.Timeout:
        st.warning(
            "A análise demorou mais que o esperado. "
            "Tente novamente."
        )

    except requests.exceptions.ConnectionError:
        st.error(
            "Não foi possível conectar ao FastAPI. "
            "Verifique se o backend está funcionando."
        )

    except requests.exceptions.RequestException as erro:
        st.error(f"Erro de comunicação com a API: {erro}")

    except ValueError:
        st.error("A API retornou um JSON inválido.")


def show_saved_feedback():
    st.subheader("Feedbacks salvos no MongoDB")
    st.caption("Até 100 registros, dos mais recentes para os mais antigos.")
    st.button("Atualizar lista")

    try:
        feedback_list = requests.get(
            f"http://{fastapi_host}:8000/feedback/",
            timeout=40,
        )
        if not feedback_list.ok:
            try:
                error = feedback_list.json()
                detail = error.get("detail", "Falha na consulta.") if isinstance(error, dict) else "Resposta inesperada."
            except ValueError:
                detail = "O servidor retornou uma resposta inválida."
            st.error(f"Não foi possível carregar os feedbacks (HTTP {feedback_list.status_code}): {detail}")
            return
        documents = feedback_list.json()
        if not isinstance(documents, list) or not all(
            isinstance(document, dict) for document in documents
        ):
            st.error("A API retornou uma lista inválida.")
            return
    except requests.exceptions.Timeout:
        st.warning("A consulta demorou mais que o esperado. Tente atualizar novamente.")
        return
    except requests.exceptions.RequestException:
        st.error("Não foi possível consultar o backend. Verifique se ele está funcionando.")
        return
    except ValueError:
        st.error("A API retornou um JSON inválido.")
        return

    if not documents:
        st.info("Nenhum feedback salvo ainda. Envie um comentário na aba de análise.")
        return

    rows = []
    for document in documents:
        result = document.get("response")
        result = result if isinstance(result, dict) else {}
        rows.append({
            "Comentário": document.get("comment", ""),
            "Avaliação": document.get("rating"),
            "Descrição": document.get("descricao", result.get("descricao", "Não registrada")),
            "Status": document.get("status", result.get("status", "Não registrado")),
            "ID": document.get("_id", ""),
        })
    st.dataframe(rows, hide_index=True, width="stretch")


st.title("Análise de Sentimentos")
analysis_tab, history_tab = st.tabs(["Analisar comentário", "Feedbacks salvos"])

with analysis_tab:
    comment = st.text_input("Escreva seu comentário aqui:")
    rating = st.slider("Avaliação (1 a 5 estrelas):", 1, 5, 3)

    if st.button("Enviar"):
        submit_comment(comment, rating)

with history_tab:
    show_saved_feedback()
