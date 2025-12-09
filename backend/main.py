import os
import json
from pathlib import Path
from typing import List, Optional

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# =========================
# CONFIG BÁSICA
# =========================

BASE_DIR = Path(__file__).parent
DB_PRODUTOS = BASE_DIR / "produtos.json"
DB_PAGAMENTOS = BASE_DIR / "17c8373f22c68cadfae710549f71d730dc341edcf026864e72756fec82b4cb35"

# 1) AGORA CERTO: pega o token da variável de ambiente MP_ACCESS_TOKEN
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")

if not MP_ACCESS_TOKEN:
    raise RuntimeError(
        MP_ACCESS_TOKEN = " "17c8373f22c68cadfae710549f71d730dc341edcf026864e72756fec82b4cb35""
        "Defina a variável de ambiente MP_ACCESS_TOKEN com o token do Mercado Pago."
    )

MP_API_BASE = "https://api.mercadopago.com"

# 2) URL pública do BACKEND (quando estiver hospedado: Render, Railway etc.)
#    --> TROCAR QUANDO PUBLICAR O BACKEND
BASE_PUBLIC_URL = os.getenv(
    "BASE_PUBLIC_URL",
    "https://SEU-BACKEND-AQUI.com"  # ex.: https://nicolly-backend.onrender.com
)

# 3) (Opcional) URLs de retorno do checkout do Mercado Pago
FRONT_BASE_URL = os.getenv(
    "FRONT_BASE_URL",
    "https://nicoosavoy.netlify.app"  # troque pelo seu domínio real da página da Nicolly
)


# =========================
# MODELOS Pydantic
# =========================

class ProdutoIn(BaseModel):
    nome: str
    descricao: Optional[str] = None
    preco: float
    tipo: str = "digital"          # "digital" ou "fisico"
    precisa_frete: bool = False
    imagem_url: Optional[str] = None


class Produto(ProdutoIn):
    id: int


class PagamentoStatus(BaseModel):
    external_reference: str
    status: str          # ex: "approved", "pending", "rejected"
    raw: dict            # JSON completo retornado pelo MP (para auditoria)


class CriarPagamentoNicollyRequest(BaseModel):
    """
    Dados que o front da Nicolly envia para criar o link de pagamento.
    external_reference = WhatsApp ou e-mail da compradora.
    """
    external_reference: str


# =========================
# UTIL: ARQUIVOS JSON "BANCO"
# =========================

def _carregar_json(caminho: Path, default):
    if not caminho.exists():
        return default
    try:
        with caminho.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _salvar_json(caminho: Path, dados):
    with caminho.open("w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def carregar_produtos() -> List[Produto]:
    data = _carregar_json(DB_PRODUTOS, [])
    return [Produto(**p) for p in data]


def salvar_produtos(lista: List[Produto]):
    _salvar_json(DB_PRODUTOS, [p.model_dump() for p in lista])


def carregar_pagamentos() -> List[PagamentoStatus]:
    data = _carregar_json(DB_PAGAMENTOS, [])
    return [PagamentoStatus(**p) for p in data]


def salvar_pagamentos(lista: List[PagamentoStatus]):
    _salvar_json(DB_PAGAMENTOS, [p.model_dump() for p in lista])


# =========================
# INTEGRAÇÃO MERCADO PAGO
# =========================

def consultar_pagamento_mp(payment_id: str) -> dict:
    """
    Consulta o pagamento no Mercado Pago usando o id recebido no webhook.
    """
    url = f"{MP_API_BASE}/v1/payments/{payment_id}"
    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
    resp = requests.get(url, headers=headers, timeout=10)

    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao consultar pagamento no Mercado Pago: {resp.text}",
        )

    return resp.json()


def gravar_status_pagamento(status_json: dict):
    """
    Salva/atualiza status de um pagamento no 'banco' local (pagamentos.json).
    Usa external_reference como chave (por ex, e-mail ou WhatsApp do cliente).
    """
    external_reference = status_json.get("external_reference")
    status = status_json.get("status")

    if not external_reference:
        # Sem external_reference não conseguimos amarrar ao usuário.
        return

    pagamentos = carregar_pagamentos()
    # remove registros antigos dessa referência
    pagamentos = [
        p for p in pagamentos
        if p.external_reference != external_reference
    ]
    pagamentos.append(PagamentoStatus(
        external_reference=external_reference,
        status=status,
        raw=status_json,
    ))
    salvar_pagamentos(pagamentos)


def obter_status_por_reference(external_reference: str) -> Optional[PagamentoStatus]:
    pagamentos = carregar_pagamentos()
    for p in pagamentos:
        if p.external_reference == external_reference:
            return p
    return None


# =========================
# FASTAPI
# =========================

app = FastAPI(title="Backend Pagamentos – Plataforma WS / Nicolly")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # em produção, pode restringir ao domínio do front
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# ENDPOINTS DE PRODUTOS (GENÉRICOS)
# =========================

@app.get("/produtos", response_model=List[Produto])
def listar_produtos():
    """
    Lista todos os produtos cadastrados.
    Futuro: o front pode parar de usar localStorage e buscar daqui.
    """
    return carregar_produtos()


@app.post("/produtos", response_model=Produto)
def criar_produto(produto: ProdutoIn):
    """
    Cria um novo produto e retorna com ID gerado.
    Pode ser chamado pelo painel admin (no futuro).
    """
    produtos = carregar_produtos()
    novo_id = max([p.id for p in produtos], default=0) + 1
    novo = Produto(id=novo_id, **produto.model_dump())
    produtos.append(novo)
    salvar_produtos(produtos)
    return novo


# =========================
# CRIAR PREFERÊNCIA – E-BOOK NICOLLY
# =========================

@app.post("/pagamento/nicolly/preferencia")
def criar_preferencia_nicolly(payload: CriarPagamentoNicollyRequest):
    """
    O front da Nicolly chama este endpoint para criar um link de pagamento
    do e-book "O Poder do Primeiro Passo".

    external_reference = WhatsApp ou e-mail da compradora.
    """
    url = f"{MP_API_BASE}/checkout/preferences"
    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    body = {
        "items": [
            {
                "title": "E-book O Poder do Primeiro Passo",
                "description": "E-book digital de NICÓLLY SAVOY",
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": 29.90,
            }
        ],
        "external_reference": payload.external_reference,
        "notification_url": f"{BASE_PUBLIC_URL}/webhook/mercadopago",
        "back_urls": {
            "success": FRONT_BASE_URL,
            "failure": FRONT_BASE_URL,
            "pending": FRONT_BASE_URL,
        },
        "auto_return": "approved",
    }

    resp = requests.post(url, headers=headers, json=body, timeout=15)
    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao criar preferência no Mercado Pago: {resp.text}",
        )

    data = resp.json()
    return {
        "id": data.get("id"),
        "init_point": data.get("init_point"),
        "sandbox_init_point": data.get("sandbox_init_point"),
        "external_reference": payload.external_reference,
    }


# =========================
# WEBHOOK MERCADO PAGO
# =========================

@app.post("/webhook/mercadopago")
async def mercadopago_webhook(request: Request):
    """
    Endpoint chamado pelo Mercado Pago quando há atualização de pagamento.

    No painel do Mercado Pago, configure:
    notification_url = BASE_PUBLIC_URL + "/webhook/mercadopago"
    """
    payload = await request.json()

    payment_id = None
    if isinstance(payload, dict):
        data = payload.get("data") or {}
        payment_id = data.get("id") or payload.get("id")

    if not payment_id:
        raise HTTPException(status_code=400, detail="Payload sem payment_id válido.")

    status_json = consultar_pagamento_mp(str(payment_id))
    gravar_status_pagamento(status_json)

    return {"received": True, "payment_id": payment_id}


# =========================
# CONSULTA SE USUÁRIO JÁ PAGOU
# =========================

@app.get("/pagamento/status/{external_reference}")
def pagamento_status(external_reference: str):
    """
    O front chama este endpoint perguntando:
    "esse external_reference já está aprovado?"

    external_reference pode ser:
    - e-mail do cliente
    - número de telefone/whatsapp
    """
    info = obter_status_por_reference(external_reference)
    if not info:
        return {"external_reference": external_reference, "approved": False}

    return {
        "external_reference": external_reference,
        "approved": info.status == "approved",
        "status": info.status,
    }


# =========================
# ROTA RAIZ (OPCIONAL)
# =========================

@app.get("/")
def raiz():
    return {
        "msg": "Backend de pagamentos rodando.",
        "mercado_pago_notification_url": f"{BASE_PUBLIC_URL}/webhook/mercadopago",
    }


# Para rodar direto com: python app.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
