import debounce from "https://cdn.skypack.dev/lodash.debounce";

const { Application, Controller } = window.Stimulus;
const application = Application.start();

const renderUserMessage = (content) =>
  `<div class="text-right font-bold mb-2">${content}</div>`;

const renderAssistantMessage = (content) =>
  `<div class="mb-2">${content || ""}</div>`;

const renderCard = (card) => `
  <div class="my-4 p-4 border rounded">
    <h3 class="text-lg font-semibold">${card.title}</h3>
    <p class="mt-2 text-sm">${card.description}</p>
    ${card.video ? `<video controls class="mt-4 w-full rounded"><source src="${card.video}" type="video/mp4"></video>` : ""}
  </div>
`;

class ChatController extends Controller {
  static targets = ["input", "suggestions", "messages"];

  connect() {
    this.searchAbortController = null;
    this.search = debounce(this._search.bind(this), 400);
  }

  onInput() {
    const query = this.inputTarget.value.trim();
    if (query) {
      this.search(query);
    } else {
      this.clearSuggestions();
    }
  }

  async send(event) {
    event.preventDefault();
    const query = this.inputTarget.value.trim();
    if (!query) return;

    const resp = await fetch(`/search?q=${encodeURIComponent(query)}`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    const { messages } = await resp.json();

    // Отрисовываем историю заново
    this.messagesTarget.innerHTML = "";
    messages.forEach((msg) => {
      if (msg.role === "user") {
        this.messagesTarget.insertAdjacentHTML("beforeend", renderUserMessage(msg.content));
      } else {
        this.messagesTarget.insertAdjacentHTML("beforeend", renderAssistantMessage(msg.content));
        msg.cards?.forEach((card) => this.messagesTarget.insertAdjacentHTML("beforeend", renderCard(card)));
      }
    });

    // Скроллим к последнему сообщению
    this.messagesTarget.scrollTop = this.messagesTarget.scrollHeight;
  }

  async clear() {
    this.messagesTarget.innerHTML = "";
    await fetch("/search/?clear=1");
  }

  // Автодополнение
  async _search(query) {
    // Отмена предыдущего запроса
    this.searchAbortController?.abort();
    this.searchAbortController = new AbortController();

    this.showLoading();

    try {
      const resp = await fetch(`/suggestions?q=${encodeURIComponent(query)}`, {
        signal: this.searchAbortController.signal,
      });
      const items = await resp.json();

      // Если пользователь успел набрать новый текст – игнорируем ответ
      if (this.inputTarget.value.trim() !== query) return;

      this.showSuggestions(items);
    } catch (error) {
      if (error.name !== "AbortError") {
        console.error(error);
        this.clearSuggestions();
      }
    } finally {
      this.hideLoading();
    }
  }

  showSuggestions(items) {
    if (items.length === 0) return this.clearSuggestions();

    const list = items
      .map(
        (i) => `
        <div class="suggestion-item px-4 py-2 hover:bg-gray-200 cursor-pointer rounded transition" data-id="${i.id}" data-value="${i.text}">
          ${i.text}
        </div>`
      )
      .join("");

    this.suggestionsTarget.innerHTML = `
      <div class="suggestion-message bg-gray-100 border border-gray-200 rounded-lg shadow-sm my-4">
        ${list}
      </div>`;
  }

  clearSuggestions() {
    this.suggestionsTarget.innerHTML = "";
  }

  select(event) {
    const el = event.target.closest(".suggestion-item");
    if (!el) return;

    this.inputTarget.value = el.dataset.value;
    this.clearSuggestions();
    this.inputTarget.form.requestSubmit();
  }

  showLoading() {
    this.clearSuggestions();
    this.suggestionsTarget.innerHTML =
      '<div class="loading-message px-4 py-2 text-gray-500 italic">Загрузка...</div>';
  }

  hideLoading() {
    this.suggestionsTarget.querySelector(".loading-message")?.remove();
  }
}

application.register("chat", ChatController);
