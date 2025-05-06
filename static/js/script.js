window.onload = function () {
  const path = window.location.pathname;

  //Recommendation Cards (on recommendations.html)
  if (path.includes("recommendations")) {
    const params = new URLSearchParams(window.location.search);
    const genre = params.get("genre");
    const type = params.get("type");

    fetch(`/api/recommend?type=${type}&genre=${genre}`)
      .then(res => res.json())
      .then(data => {
        const container = document.getElementById("cards");
        container.innerHTML = "";

        if (data.length === 0) {
          container.innerHTML = "<p>No recommendations found.</p>";
          return;
        }

        const fallbackImage = {
          book: "/static/images/Books_Default.png",
          movie: "/static/images/2503508.png"
        };

        data.forEach((item, i) => {
          const card = document.createElement("div");
          card.className = `card pastel${(i % 10) + 1}`;

          const imageUrl = item.image && item.image.trim() !== "" ? item.image : fallbackImage[item.type];

          card.innerHTML = `
            <a href="/details?title=${encodeURIComponent(item.title)}&type=${item.type}">
              <img src="${imageUrl}" alt="${item.title}">
              <h3>${item.title}</h3>
              <p>⭐ ${item.rating.toFixed(2)}</p>
            </a>
          `;
          container.appendChild(card);
        });
      });
  }

  //Item Details (on details.html)
  if (path.includes("details")) {
    const params = new URLSearchParams(window.location.search);
    const title = params.get("title");
    const type = params.get("type");

    fetch(`/api/details?title=${encodeURIComponent(title)}&type=${type}`)
      .then(res => res.json())
      .then(data => {
        const container = document.getElementById("details");

        const fallbackImage = {
          book: "/static/images/Books_Default.png",
          movie: "/static/images/2503508.png"
        };

        const imageUrl = data.image && data.image.trim() !== "" ? data.image : fallbackImage[data.type];

        if (data.error) {
          container.innerHTML = "<p>Item not found.</p>";
        } else {
          container.innerHTML = `
            <div class="detail-box">
              <h2>${data.title}</h2>
              <img src="${imageUrl}" class="detail-img" alt="${data.title}">
              ${data.type === "book" ? `<p><strong>Author:</strong> ${data.author || "Unknown"}</p>` : ""}
              <p><strong>Year:</strong> ${data.year}</p>
              <p><strong>Rating:</strong> ⭐ ${data.rating.toFixed(2)}</p>
              <p>${data.content}</p>
            </div>
          `;
        }
      });
  }
};
