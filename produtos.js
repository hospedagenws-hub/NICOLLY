// frontend/produtos.js

// === CONFIGURAÇÕES BÁSICAS ===

// URL pública do backend (amanhã, quando subir no Render/Railway, você troca aqui)
const BACKEND_URL = "https://SEU-BACKEND-AQUI.onrender.com";

// ID dos elementos que já existem no index da Nicolly
const btnJaPaguei    = document.getElementById("btnJaPaguei");
const ebookArea      = document.getElementById("ebookArea");
const ebookAviso     = document.getElementById("ebookAviso");

// chave para guardar no navegador qual identificador a cliente usou
const STORAGE_EXTERNAL_REF = "nicolly_external_reference";
const STORAGE_EBOOK_OK     = "ebookLiberado_nicolly_real";

/**
 * Atualiza a interface de acordo com o estado salvo em localStorage.
 * Se já estiver liberado, mostra a área de download sempre.
 */
function atualizarUIEbook() {
  const liberado = localStorage.getItem(STORAGE_EBOOK_OK) === "1";

  if (!ebookArea || !ebookAviso) return;

  if (liberado) {
    ebookArea.classList.remove("hidden");
    ebookAviso.classList.add("hidden");
  } else {
    ebookArea.classList.add("hidden");
    ebookAviso.classList.remove("hidden");
  }
}

/**
 * Consulta o backend para saber se o pagamento com essa external_reference
 * já está como "approved".
 */
async function consultarPagamento(externalRef) {
  try {
    const url = `${BACKEND_URL}/pagamento/status/${encodeURIComponent(
      externalRef
    )}`;

    const resp = await fetch(url);
    if (!resp.ok) {
      console.error("Erro ao consultar backend:", resp.status, await resp.text());
      alert(
        "Não consegui confirmar o pagamento agora. Tente novamente em alguns minutos."
      );
      return;
    }

    const data = await resp.json();
    console.log("Resposta do backend:", data);

    if (data.approved === true) {
      // Pagamento aprovado
      localStorage.setItem(STORAGE_EBOOK_OK, "1");
      atualizarUIEbook();
      alert("Pagamento aprovado! E-book liberado para download.");
    } else {
      // Ainda não aprovado
      alert(
        "Ainda não encontrei seu pagamento como aprovado.\n" +
          "Se você acabou de pagar, aguarde alguns minutos e clique de novo em 'Já paguei, liberar e-book'."
      );
    }
  } catch (err) {
    console.error("Erro na consulta de pagamento:", err);
    alert(
      "Ocorreu um erro ao tentar verificar o pagamento. Verifique sua internet e tente novamente."
    );
  }
}

/**
 * Fluxo acionado quando a cliente clica em "Já paguei, liberar e-book".
 * 1) Pergunta qual identificador ela usou (WhatsApp ou e-mail).
 * 2) Salva no localStorage.
 * 3) Chama o backend para confirmar.
 */
async function handleJaPagueiClick() {
  // Pergunta para cliente qual dado foi usado como referência
  // (TEM QUE SER O MESMO external_reference usado na preferência do Mercado Pago)
  const externalRef = prompt(
    "Digite o e-mail ou WhatsApp usado no pagamento para confirmar seu pedido:"
  );

  if (!externalRef) {
    alert("Você precisa informar o e-mail ou WhatsApp usado no pagamento.");
    return;
  }

  localStorage.setItem(STORAGE_EXTERNAL_REF, externalRef.trim());

  // Chama o backend para ver se já está aprovado
  await consultarPagamento(externalRef.trim());
}

// Liga o fluxo no botão "Já paguei, liberar e-book"
if (btnJaPaguei) {
  btnJaPaguei.addEventListener("click", (e) => {
    e.preventDefault();
    handleJaPagueiClick();
  });
}

// Na inicialização da página, garante que UI está coerente
atualizarUIEbook();
