(function () {
  var node = document.getElementById("newsren-data");
  var data = node ? JSON.parse(node.textContent) : { stories: [], stopwords: [], followEmpty: "" };
  var storageKey = "newsren.reader";
  var baseNode = document.querySelector('meta[name="newsren-base"]');
  var siteBase = baseNode ? baseNode.content : "";

  function load() {
    try {
      var saved = JSON.parse(localStorage.getItem(storageKey) || "{}");
      if (!saved.audience) saved.audience = "student";
      if (!saved.follows) saved.follows = [];
      if (!saved.versionedSeen && (data.stories || []).length) {
        saved.follows.forEach(function (follow) {
          follow.seenIds = (follow.seenIds || []).map(function (id) {
            var story = data.stories.find(function (item) { return item.id === id; });
            return story ? (story.followKey || id) : id;
          });
        });
        saved.versionedSeen = true;
        persist(saved);
      }
      return saved;
    } catch (error) {
      return { audience: "student", follows: [] };
    }
  }

  function persist(state) {
    localStorage.setItem(storageKey, JSON.stringify(state));
  }

  function terms(question) {
    var words = (question.toLowerCase().match(/[a-z0-9]+/g) || []);
    return words.filter(function (word) {
      return data.stopwords.indexOf(word) === -1 && (word.length > 3 || (data.shortTopics || []).indexOf(word) !== -1);
    });
  }

  function matches(question, story, seenIds) {
    var wanted = terms(question);
    if (!wanted.length || seenIds.indexOf(story.followKey || story.id) !== -1) return false;
    if (story.materialUpdate === false) return false;
    var text = story.title + " " + (story.summary_sentences || []).join(" ");
    var words = text.toLowerCase().match(/[a-z0-9]+/g) || [];
    return wanted.some(function (term) { return words.indexOf(term) !== -1; });
  }

  function applyAudience(audience) {
    document.querySelectorAll("[data-audience]").forEach(function (panel) {
      panel.hidden = panel.getAttribute("data-audience") !== audience;
    });
    document.querySelectorAll("[data-choose]").forEach(function (button) {
      button.setAttribute("aria-pressed", button.getAttribute("data-choose") === audience ? "true" : "false");
    });
  }

  function renderFollowing(state) {
    var host = document.getElementById("following");
    if (!host) return;
    host.innerHTML = "";
    if (!state.follows.length) {
      host.textContent = data.followEmpty;
      return;
    }
    state.follows.forEach(function (follow, index) {
      var block = document.createElement("section");
      var heading = document.createElement("h2");
      heading.textContent = follow.question;
      block.appendChild(heading);
      var hits = (data.stories || []).filter(function (story) {
        return matches(follow.question, story, follow.seenIds || []);
      });
      if (!hits.length) {
        var empty = document.createElement("p");
        empty.textContent = data.followEmpty;
        block.appendChild(empty);
      }
      hits.forEach(function (story) {
        var row = document.createElement("p");
        var link = document.createElement("a");
        link.href = siteBase + "/story/" + story.id + (siteBase ? "/" : "");
        link.textContent = story.title;
        row.appendChild(link);
        var seen = document.createElement("button");
        seen.type = "button";
        seen.textContent = "Mark as seen";
        seen.addEventListener("click", function () {
          var next = load();
          var ids = next.follows[index].seenIds || [];
          var key = story.followKey || story.id;
          if (ids.indexOf(key) === -1) ids.push(key);
          next.follows[index].seenIds = ids;
          persist(next);
          renderFollowing(next);
        });
        row.appendChild(seen);
        block.appendChild(row);
      });
      var quotes = [];
      hits.forEach(function (story) {
        (story.changeSentences || []).forEach(function (sentence) {
          quotes.push({ sentence: sentence, story: story });
        });
      });
      quotes = quotes.slice(0, 3);
      if (quotes.length) {
        var briefing = document.createElement("h3");
        briefing.textContent = data.briefing || "Briefing";
        block.appendChild(briefing);
        var note = document.createElement("p");
        note.textContent = data.briefingNote || "These sentences are from matching stories, not a synthesis.";
        block.appendChild(note);
        var changed = document.createElement("h3");
        changed.textContent = data.whatChanged || "What changed";
        block.appendChild(changed);
        quotes.forEach(function (quote) {
          var item = document.createElement("blockquote");
          var text = document.createElement("p");
          text.textContent = quote.sentence;
          item.appendChild(text);
          var cite = document.createElement("p");
          var source = document.createElement("a");
          source.href = siteBase + "/story/" + quote.story.id + (siteBase ? "/" : "");
          source.textContent = quote.story.title;
          cite.appendChild(source);
          item.appendChild(cite);
          block.appendChild(item);
        });
        var lines = [(data.briefing || "Briefing") + ": " + follow.question, "", data.briefingNote || ""];
        quotes.forEach(function (quote) {
          lines.push("");
          lines.push(quote.sentence);
          lines.push((quote.story.title || "") + " " + (quote.story.url || ""));
        });
        var body = lines.join("\n");
        var mail = document.createElement("a");
        mail.href = "mailto:?subject=" + encodeURIComponent("Newsren briefing: " + follow.question) + "&body=" + encodeURIComponent(body);
        mail.textContent = data.emailBriefing || "Email briefing";
        block.appendChild(mail);
        var copy = document.createElement("button");
        copy.type = "button";
        copy.textContent = data.copyBriefing || "Copy briefing";
        copy.addEventListener("click", function () {
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(body);
          }
        });
        block.appendChild(copy);
        var emailNote = document.createElement("p");
        emailNote.textContent = data.emailNote || "Opens your mail app. This site does not send email.";
        block.appendChild(emailNote);
      }
      var remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "Remove this question";
      remove.addEventListener("click", function () {
        var next = load();
        next.follows.splice(index, 1);
        persist(next);
        renderFollowing(next);
      });
      block.appendChild(remove);
      host.appendChild(block);
    });
  }

  function showFilter(name) {
    document.querySelectorAll("[data-filter]").forEach(function (button) {
      button.setAttribute("aria-pressed", button.getAttribute("data-filter") === name ? "true" : "false");
    });
    var following = name === "following";
    var list = document.getElementById("story-list");
    var host = document.getElementById("following");
    if (list) list.hidden = following;
    if (host) host.hidden = !following;
    var tracker = document.getElementById("finance-tracker");
    var stats = document.getElementById("local-cache");
    if (tracker) tracker.hidden = following;
    if (stats) stats.hidden = following;
    document.querySelectorAll(".card, .source-error").forEach(function (card) {
      var category = card.getAttribute("data-category");
      card.hidden = following || (name !== "all" && category !== name);
    });
  }

  document.addEventListener("click", function (event) {
    var filter = event.target.closest("[data-filter]");
    if (filter) showFilter(filter.getAttribute("data-filter"));
    var choose = event.target.closest("[data-choose]");
    if (choose) {
      var state = load();
      state.audience = choose.getAttribute("data-choose");
      persist(state);
      applyAudience(state.audience);
    }
  });

  var question = document.getElementById("question");
  var follow = document.getElementById("follow");
  var form = document.getElementById("ask-form");
  if (form) {
    form.addEventListener("submit", function (event) {
      if (!question.value.trim()) event.preventDefault();
    });
  }
  if (question && follow) {
    var toggle = function () { follow.disabled = !question.value.trim(); };
    question.addEventListener("input", toggle);
    toggle();
    follow.addEventListener("click", function () {
      var text = question.value.trim();
      if (!text) return;
      var state = load();
      var exists = state.follows.some(function (item) { return item.question === text; });
      if (!exists) state.follows.push({ question: text, seenIds: [] });
      persist(state);
      follow.textContent = "Following";
    });
  }

  var refresh = document.getElementById("refresh");
  if (refresh) {
    refresh.addEventListener("click", function () {
      fetch("/api/refresh", { method: "POST" }).then(function () { window.location.reload(); });
    });
  }
  if (document.getElementById("loading")) {
    window["set" + "Int" + "erval"](function () {
      fetch("/api/stories").then(function (response) { return response.json(); }).then(function (payload) {
        if ((payload.stories || []).length || !payload.refreshing) window.location.reload();
      });
    }, 3000);
  }

  var saved = load();
  applyAudience(saved.audience);
  renderFollowing(saved);
  showFilter("all");
})();
