// Entry point. Calls the backend health endpoint on load, which is exactly
// the kind of fetch the pipeline's frontend build step needs to see compiled.
import { fetchHealth } from './api.js';

const target = document.getElementById('health');

fetchHealth()
  .then((data) => {
    target.textContent = `Backend: ${data.status}`;
  })
  .catch((err) => {
    target.textContent = `Backend unreachable (${err.message})`;
  });
