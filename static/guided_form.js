document.addEventListener('DOMContentLoaded', () => {
  const data = window.featureData;
  const featureName = data.name;
  const lang = data.language;
  const totalSteps = data.totalSteps;
  const questions = data.questions;
  const ui = data.ui;
  
  let currentStep = 0;
  let answers = {};
  let isSubmitting = false;

  // DOM Elements
  const stepIndicator = document.getElementById('step-indicator');
  const progressFill = document.getElementById('progress-fill');
  const questionText = document.getElementById('question-text');
  const questionDesc = document.getElementById('question-desc');
  const inputContainer = document.getElementById('input-container');
  const errorMessage = document.getElementById('error-message');
  const backBtn = document.getElementById('back-btn');
  const nextBtn = document.getElementById('next-btn');
  const submitBtn = document.getElementById('submit-btn');
  const cancelBtn = document.getElementById('cancel-btn');
  const loadingScreen = document.getElementById('loading-screen');
  const loadingMessage = document.getElementById('loading-message');
  const resultContainer = document.getElementById('result-container');
  const formContainer = document.getElementById('guided-form-container');

  // Initialize form
  function initForm() {
    renderQuestion(0);
    updateProgress();
    
    // Auto-speak first question after a short delay to ensure voice state is loaded
    setTimeout(() => {
      const voiceEnabled = window.isVoiceEnabled || false;
      if (voiceEnabled && questions.length > 0) {
        const question = questions[0];
        speakText(question.text + '. ' + question.description);
      }
    }, 500);
  }

  // Render current question
  function renderQuestion(stepIndex) {
    const question = questions[stepIndex];
    questionText.textContent = question.text;
    questionDesc.textContent = question.description;
    
    // Build input based on type
    let inputHTML = '';
    if (question.type === 'number') {
      inputHTML = `<input type="number" id="current-input" 
                   min="${question.min || ''}" max="${question.max || ''}" step="${question.step || 'any'}"
                   placeholder="${question.placeholder || ''}" 
                   value="${answers[question.key] || ''}">`;
    } else if (question.type === 'select') {
      inputHTML = `<select id="current-input">`;
      inputHTML += `<option value="">${question.placeholder || ''}</option>`;
      question.options.forEach(opt => {
        const selected = answers[question.key] === opt.value ? 'selected' : '';
        inputHTML += `<option value="${opt.value}" ${selected}>${opt.label}</option>`;
      });
      inputHTML += `</select>`;
    } else if (question.type === 'textarea') {
      inputHTML = `<textarea id="current-input" rows="3" 
                   placeholder="${question.placeholder || ''}">${answers[question.key] || ''}</textarea>`;
    } else if (question.type === 'date') {
      inputHTML = `<input type="date" id="current-input" value="${answers[question.key] || ''}">`;
    }
    
    inputContainer.innerHTML = inputHTML;
    errorMessage.style.display = 'none';
    
    // Update navigation buttons
    backBtn.style.display = stepIndex === 0 ? 'none' : 'inline-block';
    if (stepIndex === totalSteps - 1) {
      nextBtn.style.display = 'none';
      submitBtn.style.display = 'inline-block';
    } else {
      nextBtn.style.display = 'inline-block';
      submitBtn.style.display = 'none';
    }

    // Auto-speak question
    // Check if voice is enabled from global scope
    const voiceEnabled = window.isVoiceEnabled || false;
    if (voiceEnabled) {
      speakText(question.text + '. ' + question.description);
    }
  }

  // Update progress bar
  function updateProgress() {
    const progress = ((currentStep + 1) / totalSteps) * 100;
    progressFill.style.width = progress + '%';
    stepIndicator.textContent = `${ui.step} ${currentStep + 1} ${ui.of} ${totalSteps}`;
  }

  // Validate current input
  function validateInput() {
    const question = questions[currentStep];
    const input = document.getElementById('current-input');
    const value = input.value.trim();
    
    if (question.required && !value) {
      errorMessage.textContent = ui.value_required;
      errorMessage.style.display = 'block';
      return false;
    }
    
    if (question.type === 'number' && value) {
      const num = parseFloat(value);
      if (isNaN(num)) {
        errorMessage.textContent = ui.invalid_value;
        errorMessage.style.display = 'block';
        return false;
      }
      if (question.min !== undefined && num < question.min) {
        errorMessage.textContent = ui.invalid_value;
        errorMessage.style.display = 'block';
        return false;
      }
      if (question.max !== undefined && num > question.max) {
        errorMessage.textContent = ui.invalid_value;
        errorMessage.style.display = 'block';
        return false;
      }
    }
    
    return true;
  }

  // Handle Next button
  nextBtn.addEventListener('click', () => {
    if (!validateInput()) return;
    
    const question = questions[currentStep];
    const input = document.getElementById('current-input');
    answers[question.key] = input.value.trim();
    
    currentStep++;
    updateProgress();
    renderQuestion(currentStep);
  });

  // Handle Back button
  backBtn.addEventListener('click', () => {
    const question = questions[currentStep];
    const input = document.getElementById('current-input');
    answers[question.key] = input.value.trim();
    
    currentStep--;
    updateProgress();
    renderQuestion(currentStep);
  });

  // Handle Submit button
  submitBtn.addEventListener('click', async () => {
    if (!validateInput()) return;
    if (isSubmitting) return;
    
    const question = questions[currentStep];
    const input = document.getElementById('current-input');
    answers[question.key] = input.value.trim();
    
    isSubmitting = true;
    formContainer.style.display = 'none';
    loadingScreen.style.display = 'block';
    
    // Set appropriate loading message
    if (featureName === 'health') {
      loadingMessage.textContent = ui.checking;
    } else if (featureName === 'water') {
      loadingMessage.textContent = ui.getting_advice;
    } else if (featureName === 'harvest') {
      loadingMessage.textContent = ui.estimating;
    }
    
    try {
      const formData = new FormData();
      for (const [key, value] of Object.entries(answers)) {
        formData.append(key, value);
      }
      formData.append('feature', featureName);
      
      let endpoint = '';
      if (featureName === 'health') endpoint = '/api/analyze';
      else if (featureName === 'water') endpoint = '/api/irrigation';
      else if (featureName === 'harvest') endpoint = '/api/maturity';
      
      const response = await fetch(endpoint, { method: 'POST', body: formData });
      const data = await response.json();
      
      loadingScreen.style.display = 'none';
      
      if (data.error) {
        alert(data.error);
        formContainer.style.display = 'block';
      } else {
        displayResult(data);
      }
    } catch (err) {
      loadingScreen.style.display = 'none';
      alert(ui.error);
      formContainer.style.display = 'block';
    } finally {
      isSubmitting = false;
    }
  });

  // Handle Cancel button
  cancelBtn.addEventListener('click', () => {
    if (confirm('Are you sure you want to cancel?')) {
      window.location.href = '/';
    }
  });

  // Display result
  function displayResult(data) {
    resultContainer.style.display = 'block';
    let resultHTML = '';
    
    if (featureName === 'health') {
      resultHTML = renderHealthResult(data);
    } else if (featureName === 'water') {
      resultHTML = renderWaterResult(data);
    } else if (featureName === 'harvest') {
      resultHTML = renderHarvestResult(data);
    }
    
    resultHTML += `<button id="retry-btn" class="button secondary" style="margin-top: 1rem;">${ui.retry}</button>`;
    
    resultContainer.innerHTML = resultHTML;
    
    // Add retry button handler
    document.getElementById('retry-btn').addEventListener('click', () => {
      resultContainer.style.display = 'none';
      formContainer.style.display = 'block';
      currentStep = 0;
      updateProgress();
      renderQuestion(0);
    });
    
    // Auto-speak result
    const voiceEnabled = window.isVoiceEnabled || false;
    if (voiceEnabled) {
      const textToSpeak = resultContainer.textContent;
      speakText(textToSpeak);
    }
  }

  // Render health result
  function renderHealthResult(data) {
    return `
      <div class="result-content">
        <h3>Overall Health Score: ${data.health_score}/100</h3>
        <p><strong>Health Status:</strong> ${data.result}</p>
        <div class="result-details">
          ${data.detailed_scores ? Object.entries(data.detailed_scores).map(([key, val]) => 
            `<p><strong>${key}:</strong> ${val}</p>`
          ).join('') : ''}
        </div>
      </div>
    `;
  }

  // Render water result
  function renderWaterResult(data) {
    return `
      <div class="result-content">
        <h3>Watering recommendation: ${data.advice}</h3>
        <p><strong>Reason:</strong> ${data.reason}</p>
        <p><strong>Priority:</strong> ${data.priority}</p>
        <p><strong>Water stress score:</strong> ${data.water_stress_score}/100</p>
      </div>
    `;
  }

  // Render harvest result
  function renderHarvestResult(data) {
    return `
      <div class="result-content">
        <h3>Estimated harvest: ${data.estimate}</h3>
        <p><strong>Expected yield:</strong> ${data.yield_kg_per_acre} kg/acre</p>
        <p><strong>Days to typical harvest time:</strong> ${data.days_remaining}</p>
        <div class="progress-bar">
          <div class="progress-fill" style="width: ${data.progress}%"></div>
        </div>
        <small>${data.progress}% toward harvest readiness</small>
      </div>
    `;
  }

  // Initialize
  initForm();
});
