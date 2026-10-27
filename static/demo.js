/* Static-only extractive Ask: quote exported evidence, never call a model. */
(function () {
  "use strict";
  var form = document.getElementById("ask-form");
  var node = document.getElementById("static-ask-data");
  if (!form || !node) return;
  var data = JSON.parse(node.textContent);
  var output = document.createElement("div");
  output.setAttribute("aria-live", "polite");
  form.after(output);
  var question = document.getElementById("question");
  function showQuotes() {
    output.replaceChildren();
    var terms = (question.value.toLowerCase().match(/[a-z0-9]+/g) || []).filter(function (word) {
      return data.stopwords.indexOf(word) === -1;
    });
    var hits = [];
    data.stories.forEach(function (story) {
      var sentences = [];
      [story.title, story.excerpt].forEach(function (part) {
        (part || "").split(/(?<=[.!?])\s+/).forEach(function (sentence) {
          if (sentence && sentences.indexOf(sentence) === -1) sentences.push(sentence);
        });
      });
      sentences.map(function (sentence, index) {
        var words = sentence.toLowerCase().match(/[a-z0-9]+/g) || [];
        return { sentence: sentence, index: index, score: terms.filter(function (term) { return words.indexOf(term) !== -1; }).length };
      }).filter(function (row) { return row.score; }).sort(function (a, b) {
        return b.score - a.score || a.index - b.index;
      }).slice(0, 3).sort(function (a, b) { return a.index - b.index; }).forEach(function (row) {
        if (hits.length < 6) hits.push({ story: story, sentence: row.sentence });
      });
    });
    var note = document.createElement("p");
    note.textContent = hits.length ? "Quoted from this story and its connected saved sources. Keyword matches, not a synthesis or a factual verdict." : "No supporting passages were found in this saved story and its connected sources.";
    output.appendChild(note);
    hits.forEach(function (hit) {
      var quote = document.createElement("blockquote");
      var text = document.createElement("p");
      text.textContent = hit.sentence;
      var link = document.createElement("a");
      link.href = hit.story.url;
      link.textContent = hit.story.source_name + " · " + hit.story.title;
      quote.append(text, link);
      output.appendChild(quote);
    });
  }
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (question.value.trim()) showQuotes();
  });
})();
