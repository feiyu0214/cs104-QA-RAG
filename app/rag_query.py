# app/rag_query.py

import time
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.schema import QueryBundle
from llama_index.core.prompts import PromptTemplate
from prompt.prompt_lib import get_prompt, list_prompts



INDEX_PATH = "data/processed/index"
storage_context = StorageContext.from_defaults(persist_dir=INDEX_PATH)
index = load_index_from_storage(storage_context)


PROMPT_NAME = "TA"   # "TA", "ta_strict"
qa_prompt = get_prompt(PROMPT_NAME)



llm = OpenAI(model="gpt-4o-mini", temperature=0)
embed_model = OpenAIEmbedding(model="text-embedding-3-small")

retriever = index.as_retriever(similarity_top_k=10)   # 只负责检索
query_engine = index.as_query_engine(
    similarity_top_k=10,
    llm=llm,
    embed_model=embed_model,
    text_qa_template=qa_prompt
)

def is_valid_query(q: str) -> bool:
    if not q:
        return False
    q = q.strip()
    if len(q) < 3:
        return False
    # 纯数字 / 数字为主的输入，直接拒绝
    if q.replace(".", "", 1).isdigit():
        return False
    return True


def safe_query(q: str, retries=5, backoff=1.5):
    if not is_valid_query(q):
        raise ValueError("Query is not a valid natural-language question.")
    # 先确保 query embedding 成功（避免 None）
    last_err = None
    for i in range(retries):
        try:
            emb = embed_model.get_query_embedding(q)
            if emb is None:
                raise RuntimeError("Query embedding returned None")
            break
        except Exception as e:
            last_err = e
            time.sleep(backoff ** i)
    else:
        raise RuntimeError(f"Embedding failed after {retries} retries: {last_err}")

    # embedding 成功后再走正常 query（此时基本不会 NoneType*float）
    return query_engine.query(q)


while True:
    q = input("Student: ").strip()

    if q.lower() in {"quit", "exit"}:
        print("TA: Bye! 👋")
        break

    if not q:
        continue

    try:
        resp = safe_query(q)
        print("\n[VirtualTA]\n", resp)

        # print("requested top_k =", 10)
        # print("returned source_nodes =", len(resp.source_nodes))

        # for i, sn in enumerate(resp.source_nodes, 1):
        #     url = sn.metadata.get("url")
        #     print(f"[{i}] score={sn.score:.4f} url={url}")

        seen = set()
        print("[Sources]")
        for sn in resp.source_nodes:
            url = sn.metadata.get("url")
            if url and url not in seen:
                print("-", url)
                seen.add(url)
        print('\n')
    except ValueError:
        print("\nTA: Could you please ask a complete question about the course?\n")
    except Exception as e:
        print("\n[Error] Query failed:", e, "\n")


