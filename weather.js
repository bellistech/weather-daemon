(() => {
  const WEATHER_URL = '/weather/weather_forecast.json';
  const REFRESH_INTERVAL_MS = 30 * 1000;
  const root = document.querySelector('[data-weather]');
  if (!root) return;

  const els = {
    location: root.querySelector('[data-weather-location]'),
    updated: root.querySelector('[data-weather-updated]'),
    nowTemp: root.querySelector('[data-weather-now-temp]'),
    nowDesc: root.querySelector('[data-weather-now-desc]'),
    nowRange: root.querySelector('[data-weather-now-range]'),
    daily: root.querySelector('[data-weather-daily]'),
    hourly: root.querySelector('[data-weather-hourly]'),
    feedPath: root.querySelector('[data-weather-feed]'),
    feedLink: root.querySelector('[data-weather-feed-link]')
  };

  const setText = (el, value) => {
    if (!el || value === undefined || value === null || value === '') return;
    el.textContent = value;
  };

  const joinParts = (parts, separator) => parts.filter(Boolean).join(separator);

  const formatTemp = (value) => {
    if (value === undefined || value === null || value === '') return '';
    const num = Number(value);
    if (Number.isNaN(num)) return String(value);
    return `${Math.round(num)}°`;
  };

  const formatUpdated = (value) => {
    if (!value) return '';
    if (typeof value === 'string' && value.toLowerCase().startsWith('updated')) {
      return value;
    }
    const date = new Date(value);
    if (!Number.isNaN(date.getTime())) {
      const formatted = new Intl.DateTimeFormat('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        timeZoneName: 'short'
      }).format(date);
      return `Updated ${formatted}`;
    }
    return String(value);
  };

  const buildDailyList = (daily) => {
    if (!els.daily || !Array.isArray(daily)) return;
    els.daily.innerHTML = '';
    daily.slice(0, 6).forEach((day) => {
      const item = document.createElement('li');
      const dayEl = document.createElement('span');
      dayEl.className = 'day';
      dayEl.textContent = day.day || day.label || day.name || '';

      const rangeEl = document.createElement('span');
      rangeEl.className = 'range';
      const high = formatTemp(day.high ?? day.hi ?? day.temp_high);
      const low = formatTemp(day.low ?? day.lo ?? day.temp_low);
      rangeEl.textContent = joinParts([high, low], ' / ');

      const condEl = document.createElement('span');
      condEl.className = 'cond';
      const cond = joinParts(
        [day.summary || day.condition || day.desc, day.icon || day.emoji],
        ' '
      );
      condEl.textContent = cond;

      item.append(dayEl, rangeEl, condEl);
      els.daily.appendChild(item);
    });
  };

  const buildHourlyRow = (hourly) => {
    if (!els.hourly || !Array.isArray(hourly)) return;
    els.hourly.innerHTML = '';
    hourly.slice(0, 12).forEach((hour) => {
      const slot = document.createElement('div');
      slot.className = 'hourly-slot';
      slot.setAttribute('role', 'listitem');

      const timeEl = document.createElement('span');
      timeEl.className = 'time';
      timeEl.textContent = hour.time || hour.label || '';

      const tempEl = document.createElement('span');
      tempEl.className = 'temp';
      tempEl.textContent = formatTemp(hour.temp ?? hour.temperature);

      const iconEl = document.createElement('span');
      iconEl.className = 'icon';
      iconEl.textContent = hour.icon || hour.emoji || '';

      slot.append(timeEl, tempEl, iconEl);
      els.hourly.appendChild(slot);
    });
  };

  const renderWeather = (data) => {
    if (!data || typeof data !== 'object') return;

    setText(els.location, data.location);
    setText(els.updated, formatUpdated(data.updated_display || data.updated));

    if (data.now && typeof data.now === 'object') {
      setText(els.nowTemp, formatTemp(data.now.temp));
      setText(els.nowDesc, joinParts([data.now.summary, data.now.icon], ' '));

      const high = formatTemp(data.now.high ?? data.now.hi);
      const low = formatTemp(data.now.low ?? data.now.lo);
      const precip = data.now.precip ?? data.now.precip_chance;
      const precipText =
        precip === undefined || precip === null || precip === ''
          ? ''
          : `${Math.round(Number(precip))}% precip`;

      const rangeText = joinParts(
        [
          joinParts([high && `H ${high}`, low && `L ${low}`], ' / '),
          precipText
        ],
        ' · '
      );
      setText(els.nowRange, rangeText);
    }

    buildDailyList(data.daily);
    buildHourlyRow(data.hourly);

    const feedPath =
      data.feed?.path || data.feed_path || data.path || WEATHER_URL;
    setText(els.feedPath, feedPath);
    if (els.feedLink && feedPath) {
      els.feedLink.setAttribute('href', feedPath);
    }
  };

  const buildUrl = () => {
    try {
      const url = new URL(WEATHER_URL, window.location.href);
      url.searchParams.set('t', Date.now().toString());
      return url.toString();
    } catch (err) {
      return WEATHER_URL;
    }
  };

  const loadWeather = async () => {
    try {
      const resp = await fetch(buildUrl(), { cache: 'no-store' });
      if (!resp.ok) return;
      const data = await resp.json();
      renderWeather(data);
      root.setAttribute('data-weather-ready', 'true');
    } catch (err) {
      console.warn('Weather load failed:', err);
    }
  };

  const scheduleRefresh = () => {
    window.setInterval(loadWeather, REFRESH_INTERVAL_MS);
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        loadWeather();
      }
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener(
      'DOMContentLoaded',
      () => {
        loadWeather();
        scheduleRefresh();
      },
      { once: true }
    );
  } else {
    loadWeather();
    scheduleRefresh();
  }
})();

