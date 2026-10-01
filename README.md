<div align="center">
  <img src="frontend/public/compass-logo.png" alt="Compass logo" width="104" />
  <h1>Compass</h1>
  <p><strong>Open-source decision infrastructure for teams that want fewer opinions and better reasons.</strong></p>
  <p>Frame a decision, compare options, attach evidence, gather review, and keep the reasoning.</p>
</div>

## Why Compass?

Important decisions often disappear into meetings, spreadsheets, and chat threads. Compass gives teams one durable place to record:

- what is being decided;
- which options are available;
- which criteria matter;
- what evidence supports each option;
- who reviewed the proposal; and
- why the final choice was made.

Use it for product bets, vendor selection, hiring plans, policy reviews, budget allocation, grants, procurement, and operational changes.

## Features

- Searchable decision inbox
- Draft, review, and approved workflows
- Ranked option comparisons
- Weighted impact, confidence, and feasibility scores
- Evidence capture and reviewer tracking
- Local browser persistence
- Responsive desktop and mobile layouts

## Quick start

```bash
git clone https://github.com/Anudeepsrib/Decision-Support-System.git
cd Decision-Support-System/frontend
npm install
npm run dev
```

Open the URL printed by Vite. The current MVP uses seeded local data and requires no account or backend.

## Commands

```bash
npm run dev      # local development
npm run build    # type-check and production build
npm run preview  # preview the production build
```

## Structure

```text
frontend/
  public/       Brand assets and app metadata
  src/          React application and styles
  Dockerfile    Static production container
```

## Roadmap

- [x] General-purpose decision workspace
- [x] Weighted option comparison
- [x] Evidence capture and local persistence
- [ ] Configurable criteria and weights
- [ ] Shared workspaces and server persistence
- [ ] Import and export in JSON and CSV

The roadmap stays intentionally small. Open an issue with a real workflow before proposing a new abstraction.

## Contributing

Bug reports, focused pull requests, and examples from real organizational decisions are welcome. Include the workflow your change improves and a short way to verify it.

## License

No license has been selected yet. Add one before accepting external contributions.
