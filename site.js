const TMDB_API_KEY = "52d74d1b6032d1a77dccefde6d442e72";
const TMDB_IMG = "https://image.tmdb.org/t/p/w200";

function formatDateShort(dateStr) {
  if (!dateStr) return "";
  const [year, month, day] = dateStr.split("-");
  const d = new Date(Number(year), Number(month) - 1, Number(day));
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "long" });
}

function formatRange(start, end) {
  if (!start) return "";
  const first = formatDateShort(start);
  if (!end || end === start) return first;
  return `${first} – ${formatDateShort(end)}`;
}

function parseDate(dateStr) {
  if (!dateStr) return null;
  const [year, month, day] = dateStr.split("-");
  return new Date(Number(year), Number(month) - 1, Number(day));
}

function todayStart() {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}

function formatGeneratedAt(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);
  return date.toLocaleDateString("en-GB", { day: "2-digit", month: "long", year: "numeric" });
}

function byId(id) {
  return document.getElementById(id);
}

function escapeHtml(value = "") {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function blurb(text = "", limit = 140) {
  const clean = text.trim();
  if (clean.length <= limit) return clean;
  return `${clean.slice(0, limit).trim().replace(/[ ,;:-]+$/, "")}...`;
}

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Failed to load ${path}`);
  return response.json();
}

function cardActions(primary, secondary = "") {
  return `<div class="actions">${primary}${secondary}</div>`;
}

function ticketCard(event, statusLabel, primaryLabel, primaryClass, noteHtml = "") {
  const saleDateKey = event.sale_start ? event.sale_start.replaceAll("-", "") : "";
  const image = event.image_url
    ? `<img src="${escapeHtml(event.image_url)}" alt="${escapeHtml(event.name)}" />`
    : "";
  const primary = event.ticket_url
    ? `<a class="btn ${primaryClass}" href="${escapeHtml(event.ticket_url)}" target="_blank" rel="noreferrer">${primaryLabel} →</a>`
    : "";
  const reminder = event.sale_start
    ? `<a class="btn btn-secondary" href="https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(`Ticket sale opens: ${event.name}`)}&dates=${saleDateKey}/${saleDateKey}" target="_blank" rel="noreferrer">Set reminder</a>`
    : "";
  return `
    <article class="panel ticket-card">
      <div>
        <div class="status-line">${statusLabel}</div>
        <h3>${escapeHtml(event.name)}</h3>
        <div class="date-line">${escapeHtml(formatRange(event.event_start, event.event_end) || `Sale opens ${formatDateShort(event.sale_start)}`)}</div>
        <div class="body">${escapeHtml(blurb(event.description, 180))}</div>
        ${noteHtml}
        ${cardActions(primary, reminder)}
      </div>
      <div>${image}</div>
    </article>`;
}

function renderContentsList(items) {
  return items.map(item => `
    <tr>
      <td style="padding:7px 0;border-bottom:0.5px solid #ececec;">
        <a href="${item.href}" style="font-size:13px;color:#1a1a1a;text-decoration:none;font-weight:600;">${item.title}</a>
      </td>
      <td style="padding:7px 0;border-bottom:0.5px solid #ececec;font-size:12px;color:#777;text-align:right;">${item.desc}</td>
    </tr>`).join("");
}

function summaryCard(label, value, note) {
  return `
    <article class="panel summary-card">
      <div class="label">${escapeHtml(label)}</div>
      <div class="value">${escapeHtml(value)}</div>
      <div class="note">${escapeHtml(note)}</div>
    </article>`;
}

function featuredPanel(eyebrow, title, meta, body, buttonLabel, buttonHref, buttonClass, image = "", imageAlt = "") {
  return `
    <article class="panel ticket-card">
      <div>
        <div class="status-line">${escapeHtml(eyebrow)}</div>
        <h3>${escapeHtml(title)}</h3>
        <div class="date-line">${escapeHtml(meta)}</div>
        <div class="body">${escapeHtml(body)}</div>
        <div class="actions">
          <a class="btn ${buttonClass}" href="${escapeHtml(buttonHref)}" target="_blank" rel="noreferrer">${escapeHtml(buttonLabel)} →</a>
        </div>
      </div>
      <div>${image ? `<img src="${escapeHtml(image)}" alt="${escapeHtml(imageAlt || title)}" />` : ""}</div>
    </article>`;
}

function mountHome(events, weekend, agenda, moviesFeed) {
  const live = events.filter(e => e.status === "on_sale" || (e.sale_start && parseDate(e.sale_start) <= new Date()));
  const action = events.filter(e => e.status === "action_required");
  const upcoming = events.filter(e => e.status === "coming_soon" && e.sale_start).sort((a, b) => a.sale_start.localeCompare(b.sale_start));
  const spotlight = events.find(e => e.spotlight && e.spotlight_description) || upcoming[0] || live[0];
  const amsterdamPick = weekend[0] || agenda[0];
  const moviePick = (moviesFeed?.cineville || [])[0] || (moviesFeed?.trending || [])[0];

  byId("hero-stats").innerHTML = `
    <div class="stat">
      <div class="stat-label">Tickets</div>
      <div class="stat-value">${live.length} live now, ${action.length} needing setup, ${upcoming.length} coming up.</div>
    </div>
    <div class="stat">
      <div class="stat-label">Movies</div>
      <div class="stat-value">A dedicated page for Cineville picks and trending films, separate from ticket alerts.</div>
    </div>
    <div class="stat">
      <div class="stat-label">Amsterdam</div>
      <div class="stat-value">${weekend.length} weekend picks and a fuller city guide on their own page.</div>
    </div>`;

  byId("home-highlights").innerHTML = `
    ${spotlight ? `
      <article class="panel highlight-card">
        ${spotlight.image_url ? `<img src="${escapeHtml(spotlight.image_url)}" alt="${escapeHtml(spotlight.name)}" />` : ""}
        <div class="content">
          <div class="chip">Tickets</div>
          <h3>${escapeHtml(spotlight.name)}</h3>
          <div class="meta">${escapeHtml(formatRange(spotlight.event_start, spotlight.event_end) || `Sale opens ${formatDateShort(spotlight.sale_start)}`)}</div>
          <p>${escapeHtml(blurb(spotlight.description || spotlight.spotlight_description, 150))}</p>
        </div>
      </article>` : ""}
    ${moviePick ? `
      <article class="panel highlight-card">
        ${moviePick.image ? `<img src="${escapeHtml(moviePick.image)}" alt="${escapeHtml(moviePick.title)}" />` : ""}
        <div class="content">
          <div class="chip">Movies</div>
          <h3>${escapeHtml(moviePick.title)}</h3>
          <div class="meta">${escapeHtml(moviePick.meta || "Film pick")}</div>
          <p>${escapeHtml(blurb(moviePick.description, 150))}</p>
        </div>
      </article>` : ""}
    ${amsterdamPick ? `
      <article class="panel highlight-card">
        ${amsterdamPick.image_url ? `<img src="${escapeHtml(amsterdamPick.image_url)}" alt="${escapeHtml(amsterdamPick.name)}" />` : ""}
        <div class="content">
          <div class="chip">Amsterdam</div>
          <h3>${escapeHtml(amsterdamPick.name)}</h3>
          <div class="meta">${escapeHtml(amsterdamPick.date || formatRange(amsterdamPick.event_start, amsterdamPick.event_end))}</div>
          <p>${escapeHtml(blurb(amsterdamPick.description, 150))}</p>
        </div>
      </article>` : ""}
  `;
}

function renderTickets(events) {
  const now = todayStart();
  const onSale = [];
  const actionRequired = [];
  const comingUp = [];
  const spotlight = [];

  for (const event of events) {
    if (event.spotlight && event.spotlight_description) spotlight.push(event);
    if (event.status === "action_required") {
      actionRequired.push(event);
    } else if (event.status === "on_sale" || (event.sale_start && parseDate(event.sale_start) <= now && event.status !== "date_unknown")) {
      onSale.push(event);
    } else if (event.sale_start) {
      comingUp.push(event);
    }
  }

  onSale.sort((a, b) => (a.sale_start || "").localeCompare(b.sale_start || ""));
  actionRequired.sort((a, b) => (a.sale_start || "9999-12-31").localeCompare(b.sale_start || "9999-12-31"));
  comingUp.sort((a, b) => (a.sale_start || "").localeCompare(b.sale_start || ""));
  spotlight.sort((a, b) => (a.event_start || a.sale_start || "").localeCompare(b.event_start || b.sale_start || ""));

  byId("tickets-summary").innerHTML = [
    summaryCard("Live now", String(onSale.length), "Ticket windows that are already open."),
    summaryCard("Action required", String(actionRequired.length), "Things to set up before the sale opens."),
    summaryCard("Coming up", String(comingUp.length), "Tracked sale windows still ahead.")
  ].join("");

  byId("tickets-live").innerHTML = onSale.length
    ? onSale.map(event => ticketCard(event, "On sale now", "Tickets are live", "btn-green")).join("")
    : `<div class="panel empty-state">No live ticket sales right now.</div>`;

  byId("tickets-action").innerHTML = actionRequired.length
    ? actionRequired.map(event => ticketCard(
        event,
        "Get ready early",
        "Get set up",
        "btn-green",
        `<div class="sub-note">${escapeHtml(event.notes || "A few details still need confirming before reminder emails can go out.")}</div>`
      )).join("")
    : `<div class="panel empty-state">No setup actions needed right now.</div>`;

  byId("tickets-coming").innerHTML = comingUp.length
    ? `
      <div class="panel list-card" style="padding:20px 22px;">
        <table style="width:100%;border-collapse:collapse;">
          ${comingUp.slice(0, 10).map(event => `
            <tr>
              <td style="padding:10px 0;border-bottom:0.5px solid #ececec;">
                <div style="font-size:15px;font-weight:600;">${escapeHtml(event.name)}</div>
              </td>
              <td style="padding:10px 0;border-bottom:0.5px solid #ececec;font-size:14px;color:#666;text-align:right;">Sale opens ${escapeHtml(formatDateShort(event.sale_start))}</td>
            </tr>`).join("")}
        </table>
      </div>`
    : `<div class="panel empty-state">No upcoming sale windows are loaded yet.</div>`;

  byId("tickets-spotlight").innerHTML = spotlight.length
    ? spotlight.slice(0, 1).map(event => {
        const image = event.image_url ? `<img src="${escapeHtml(event.image_url)}" alt="${escapeHtml(event.name)}" />` : "";
        return `
          <article class="panel hero-card">
            ${image}
            <div class="content">
              <div class="chip">Spotlight</div>
              <h3>${escapeHtml(event.name)}</h3>
              <div class="meta">${escapeHtml(formatRange(event.event_start, event.event_end) || formatDateShort(event.sale_start))}</div>
              <p>${escapeHtml(event.spotlight_description || event.description)}</p>
              <div class="actions">
                <a class="btn btn-green" href="${escapeHtml(event.ticket_url)}" target="_blank" rel="noreferrer">More info →</a>
              </div>
            </div>
          </article>`;
      }).join("")
    : `<div class="panel empty-state">No spotlight event is set at the moment.</div>`;

  byId("tickets-all").innerHTML = `
    <div class="panel list-card" style="padding:20px 22px;">
      <table style="width:100%;border-collapse:collapse;">
        ${events
          .filter(event => event.sale_start || event.status === "action_required")
          .sort((a, b) => (a.sale_start || "9999-12-31").localeCompare(b.sale_start || "9999-12-31"))
          .map(event => `
            <tr>
              <td style="padding:10px 0;border-bottom:0.5px solid #ececec;">
                <div style="font-size:15px;font-weight:600;">${escapeHtml(event.name)}</div>
                <div class="meta">${escapeHtml(event.status.replaceAll("_", " "))}</div>
              </td>
              <td style="padding:10px 0;border-bottom:0.5px solid #ececec;font-size:14px;color:#666;text-align:right;">${escapeHtml(event.sale_start ? `Sale opens ${formatDateShort(event.sale_start)}` : "Date TBA")}</td>
            </tr>`).join("")}
      </table>
    </div>`;
}

async function fetchTmdbTrending() {
  const response = await fetch(`https://api.themoviedb.org/3/trending/movie/week?api_key=${TMDB_API_KEY}&language=en-US`);
  if (!response.ok) throw new Error("TMDB failed");
  const data = await response.json();
  return (data.results || []).slice(0, 4);
}

async function fetchCinevilleFeatured() {
  const response = await fetch("https://www.cineville.nl/films");
  if (!response.ok) throw new Error("Cineville failed");
  const html = await response.text();
  const match = html.match(/id="__NEXT_DATA__"[^>]*>(.*?)<\/script>/s);
  if (!match) throw new Error("Cineville payload missing");
  const data = JSON.parse(match[1]);
  return (data.props.pageProps.featuredFilms || []).slice(0, 4);
}

async function loadMoviesFeed() {
  const response = await fetch("movies_feed.json");
  if (!response.ok) throw new Error("movies_feed.json missing");
  return response.json();
}

function movieRowHtml(movie) {
  const image = movie.image ? `<img src="${escapeHtml(movie.image)}" alt="${escapeHtml(movie.title)}" />` : "";
  const imdbLink = movie.imdb_link || movie.imdbLink || "";
  const rating = movie.imdb ? `<a class="imdb-badge" href="${escapeHtml(imdbLink || "#")}" target="_blank" rel="noreferrer">${escapeHtml(movie.imdb)}</a>` : "";
  const linkLabel = movie.link_label || movie.linkLabel || "More info";
  const trailerBtn = movie.trailer_url
    ? `<a class="btn-trailer" href="${escapeHtml(movie.trailer_url)}" target="_blank" rel="noreferrer">▶ Trailer</a>`
    : "";
  return `
    <article class="panel movie-row">
      <div>${image}</div>
      <div>
        <h3 style="font-size:20px;margin:0;"><a href="${escapeHtml(movie.link || "#")}" target="_blank" rel="noreferrer" style="text-decoration:none;">${escapeHtml(movie.title)}</a></h3>
        <div class="movie-meta">${escapeHtml(movie.meta || "")}</div>
        <div class="body" style="margin-top:8px;">${escapeHtml(blurb(movie.description, 120))}</div>
        <div class="movie-links">
          <a href="${escapeHtml(movie.link || "#")}" target="_blank" rel="noreferrer">${escapeHtml(linkLabel)} →</a>
          ${trailerBtn}
          ${imdbLink ? `<a class="movie-imdb-link" href="${escapeHtml(imdbLink)}" target="_blank" rel="noreferrer">IMDb page →</a>` : ""}
        </div>
      </div>
      <div class="rating">${rating}</div>
    </article>`;
}

async function renderMovies() {
  let cineville = [];
  let trending = [];
  let feedInfo = {};

  try {
    feedInfo = await loadMoviesFeed();
    cineville = feedInfo.cineville || [];
    trending = feedInfo.trending || [];
  } catch (error) {
    try {
      const featured = await fetchCinevilleFeatured();
      cineville = featured.map(film => ({
        title: film.title || "",
        meta: [film.releaseYear, film.duration ? `${film.duration} min` : ""].filter(Boolean).join(" · "),
        description: film.shortDescription || film.description || "",
        image: film.poster?.url ? `${film.poster.url}?w=128&auto=format` : (film.cover?.url || ""),
        link: film.slug ? `https://www.cineville.nl/films/${film.slug}` : "https://www.cineville.nl/films",
        linkLabel: "View on Cineville"
      }));
    } catch (innerError) {
      cineville = [];
    }

    try {
      const results = await fetchTmdbTrending();
      trending = results.map(movie => ({
        title: movie.title || "",
        meta: [movie.release_date ? movie.release_date.slice(0, 4) : "", movie.runtime ? `${movie.runtime} min` : ""].filter(Boolean).join(" · "),
        description: movie.overview || "",
        image: movie.poster_path ? `${TMDB_IMG}${movie.poster_path}` : "",
        link: `https://www.themoviedb.org/movie/${movie.id}`,
        linkLabel: "View film",
        imdb: movie.vote_average ? `TMDB ${movie.vote_average.toFixed(1)}` : ""
      }));
    } catch (innerError) {
      trending = [];
    }
  }

  byId("movies-cineville").innerHTML = cineville.length
    ? cineville.map(movieRowHtml).join("")
    : `<div class="panel empty-state">Cineville picks could not be loaded in the browser right now.</div>`;

  byId("movies-trending").innerHTML = trending.length
    ? trending.map(movieRowHtml).join("")
    : `<div class="panel empty-state">Trending films could not be loaded right now.</div>`;

  byId("movies-summary").innerHTML = [
    summaryCard("Cineville", String(cineville.length), "Editorial picks that feel worth your time."),
    summaryCard("Trending", String(trending.length), "The films with the most attention this week."),
    summaryCard("Updated", formatGeneratedAt(feedInfo.generated_at) || "Live", "Static site feed with browser fallback.")
  ].join("");

  const updated = formatGeneratedAt(feedInfo.generated_at);
  byId("movies-callout").innerHTML = updated
    ? `<strong>Data freshness:</strong> this page is fed from a local movie snapshot generated on ${escapeHtml(updated)}. That is a better fit for a static site than relying entirely on live browser fetches.`
    : `<strong>Data freshness:</strong> this page can fall back to live browser fetches, but the preferred setup is to keep \`movies_feed.json\` updated and let the website read from that.`;
}

function renderAmsterdam(weekend, agenda) {
  const today = todayStart();
  const upcomingCityItems = agenda
    .filter(item => item.event_start)
    .filter(item => {
      const start = parseDate(item.event_start);
      const end = parseDate(item.event_end || item.event_start);
      return end && end >= today;
    })
    .sort((a, b) => (a.event_start || "").localeCompare(b.event_start || ""))
    .slice(0, 8);

  byId("amsterdam-summary").innerHTML = [
    summaryCard("Weekend picks", String(weekend.length), "The strongest short list for the next few days."),
    summaryCard("City dates", String(upcomingCityItems.length), "Future-facing dates that are still relevant right now."),
    summaryCard("Focus", "Curated", "This page should feel selective, not exhaustive.")
  ].join("");

  byId("amsterdam-weekend").innerHTML = weekend.length
    ? weekend.map(item => `
      <article class="panel event-row">
        <div>
          <div class="status-line">${escapeHtml(item.category || "Amsterdam")}</div>
          <h3 style="font-size:28px;">${escapeHtml(item.name)}</h3>
          <div class="date-line">${escapeHtml(item.date)} · ${escapeHtml(item.location)}</div>
          <div class="body">${escapeHtml(blurb(item.description, 170))}</div>
          <div class="actions">
            <a class="btn btn-primary" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">More info →</a>
          </div>
        </div>
        <div>${item.image_url ? `<img src="${escapeHtml(item.image_url)}" alt="${escapeHtml(item.name)}" />` : ""}</div>
      </article>`).join("")
    : `<div class="panel empty-state">No weekend picks are loaded yet.</div>`;

  byId("amsterdam-city").innerHTML = upcomingCityItems.length
    ? `
      <div class="panel list-card" style="padding:20px 22px;">
        <table style="width:100%;border-collapse:collapse;">
          ${upcomingCityItems.map(item => `
            <tr>
              <td style="padding:10px 0;border-bottom:0.5px solid #ececec;">
                <div style="font-size:15px;font-weight:600;">${escapeHtml(item.name)}</div>
                <div class="meta">${escapeHtml(item.category || "")}${item.location ? ` · ${escapeHtml(item.location)}` : ""}</div>
              </td>
              <td style="padding:10px 0;border-bottom:0.5px solid #ececec;font-size:14px;color:#666;text-align:right;">${escapeHtml(formatRange(item.event_start, item.event_end))}</td>
            </tr>`).join("")}
        </table>
      </div>`
    : `<div class="panel empty-state">No future Amsterdam city dates are loaded right now.</div>`;

  byId("amsterdam-callout").innerHTML = upcomingCityItems.length
    ? `<strong>What this page should do:</strong> keep the weekend picks sharp, then let the city guide hold the broader run of Amsterdam dates without making the newsletter carry all of it.`
    : `<strong>Data gap:</strong> the weekend picks are current, but the longer-range Amsterdam agenda needs refreshing. Once that feed is updated, this page becomes much more useful than squeezing everything into email.`;
}

function renderDashboard(events, weekend, agenda, moviesFeed) {
  const now = todayStart();
  const live = events
    .filter(event => event.status === "on_sale" || (event.sale_start && parseDate(event.sale_start) <= now && event.status !== "date_unknown"))
    .sort((a, b) => (a.sale_start || "").localeCompare(b.sale_start || ""));
  const setup = events
    .filter(event => event.status === "action_required")
    .sort((a, b) => (a.sale_start || "9999-12-31").localeCompare(b.sale_start || "9999-12-31"));
  const weekendPick = weekend[0];
  const moviePick = (moviesFeed?.cineville || [])[0] || (moviesFeed?.trending || [])[0];
  const cityCount = agenda.filter(item => item.event_start).filter(item => {
    const end = parseDate(item.event_end || item.event_start);
    return end && end >= now;
  }).length;

  byId("dashboard-summary").innerHTML = [
    summaryCard("Tickets", `${live.length} live`, `${setup.length} still need setup.`),
    summaryCard("Movies", `${(moviesFeed?.cineville || []).length + (moviesFeed?.trending || []).length} picks`, "Cineville plus what is trending."),
    summaryCard("Amsterdam", `${weekend.length} weekend picks`, `${cityCount} additional city dates still relevant.`)
  ].join("");

  const ticketsPrimary = live[0] || setup[0];
  byId("dashboard-tickets").innerHTML = ticketsPrimary
    ? `
      <div class="section-heading">
        <div class="eyebrow">Tickets</div>
        <h2>What matters first on the ticket side.</h2>
        <p>The point of the dashboard is to bring the strongest ticket action to the top without making you open the full ticket page first.</p>
      </div>
      ${featuredPanel(
        live[0] ? "Live now" : "Get ready early",
        ticketsPrimary.name,
        live[0]
          ? (formatRange(ticketsPrimary.event_start, ticketsPrimary.event_end) || `Sale opens ${formatDateShort(ticketsPrimary.sale_start)}`)
          : `Sale opens ${formatDateShort(ticketsPrimary.sale_start)}`,
        blurb(live[0] ? ticketsPrimary.description : (ticketsPrimary.notes || ticketsPrimary.description), 180),
        live[0] ? "Tickets are live" : "Get set up",
        ticketsPrimary.ticket_url || "tickets.html",
        "btn-green",
        ticketsPrimary.image_url || "",
        ticketsPrimary.name
      )}
      <div class="panel compact-list">
        <table>
          ${events
            .filter(event => event.sale_start || event.status === "action_required")
            .sort((a, b) => (a.sale_start || "9999-12-31").localeCompare(b.sale_start || "9999-12-31"))
            .slice(0, 5)
            .map(event => `
              <tr>
                <td>
                  <div style="font-size:14px;font-weight:600;">${escapeHtml(event.name)}</div>
                  <div class="meta">${escapeHtml(event.status.replaceAll("_", " "))}</div>
                </td>
                <td style="text-align:right;font-size:13px;color:#666;">${escapeHtml(event.sale_start ? `Sale opens ${formatDateShort(event.sale_start)}` : "Date TBA")}</td>
              </tr>`).join("")}
        </table>
      </div>`
    : `<div class="panel empty-state">No ticket events are loaded yet.</div>`;

  byId("dashboard-movies").innerHTML = moviePick
    ? `
      <div class="section-heading">
        <div class="eyebrow">Movies</div>
        <h2>Something worth opening this week.</h2>
        <p>The film side works best when it keeps a clear editorial point of view instead of acting like a cinema listings page.</p>
      </div>
      ${movieRowHtml(moviePick)}
      <div class="panel compact-list">
        <table>
          ${(moviesFeed?.trending || []).slice(0, 4).map(movie => `
            <tr>
              <td>
                <div style="font-size:14px;font-weight:600;">${escapeHtml(movie.title)}</div>
                <div class="meta">${escapeHtml(movie.meta || "")}</div>
              </td>
              <td style="text-align:right;font-size:13px;"><a class="inline-link" href="${escapeHtml(movie.link || 'movies.html')}" target="_blank" rel="noreferrer">${escapeHtml(movie.link_label || "Open")} →</a></td>
            </tr>`).join("")}
        </table>
      </div>`
    : `<div class="panel empty-state">Movie picks are not available right now.</div>`;

  byId("dashboard-amsterdam").innerHTML = weekendPick
    ? `
      <div class="section-heading">
        <div class="eyebrow">Amsterdam</div>
        <h2>What is worth stepping out for this weekend.</h2>
        <p>The city side should feel selective and local, not like another catch-all feed.</p>
      </div>
      ${featuredPanel(
        weekendPick.category || "Amsterdam",
        weekendPick.name,
        `${weekendPick.date} · ${weekendPick.location}`,
        blurb(weekendPick.description, 180),
        "More info",
        weekendPick.url || "amsterdam.html",
        "btn-primary",
        weekendPick.image_url || "",
        weekendPick.name
      )}`
    : `<div class="panel empty-state">Weekend picks are not available right now.</div>`;

  byId("dashboard-callout").innerHTML = `<strong>How this should work:</strong> the dashboard is the bridge between the three product pages and the newsletter. It should surface the strongest next action in each vertical, then push people into the dedicated page when they want more depth.`;
}

async function init() {
  const page = document.body.dataset.page;
  const [events, weekend, agenda, moviesFeed] = await Promise.all([
    loadJson("events_db.json").catch(() => []),
    loadJson("weekend_picks.json").catch(() => []),
    loadJson("amsterdam_agenda.json").catch(() => []),
    loadJson("movies_feed.json").catch(() => ({ cineville: [], trending: [] }))
  ]);

  if (page === "home") {
    mountHome(events, weekend, agenda, moviesFeed);
  }
  if (page === "tickets") {
    renderTickets(events);
  }
  if (page === "movies") {
    renderMovies();
  }
  if (page === "amsterdam") {
    renderAmsterdam(weekend, agenda);
  }
  if (page === "dashboard") {
    renderDashboard(events, weekend, agenda, moviesFeed);
  }
}

document.addEventListener("DOMContentLoaded", init);
