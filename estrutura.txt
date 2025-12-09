# Projeto E-book Nicolly Savoy – "O Poder do Primeiro Passo"

Landing page simples para venda do e-book da **Nicolly Savoy**, com:

- Página estática (HTML + Tailwind CDN)
- Integração com **Mercado Pago** via backend FastAPI
- Liberação automática do download do e-book após pagamento **aprovado**

---

## Estrutura de pastas

```text
nicolly-site/
├─ README.md
├─ netlify.toml          (opcional, para ajustes de build/redirects)
├─ frontend/
│  ├─ index.html         # página da Nicolly
│  ├─ produtos.js        # verifica pagamento com o backend
│  └─ assets/
│     ├─ ebook-nicolly.pdf
│     ├─ capa-ebook.png
│     └─ qr-mercadopago.png
└─ backend/
   ├─ app.py             # FastAPI + Mercado Pago webhook
   ├─ requirements.txt
   ├─ .env               # APENAS LOCAL (não subir para Git)
   ├─ produtos.json
   └─ pagamentos.json
