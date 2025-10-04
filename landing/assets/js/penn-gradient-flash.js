/**
 * Penn AI Mode Effect
 * Recreates Google's AI Mode rainbow effect with Penn colors
 */

(function() {
  'use strict';

  // Penn Gradient Mode API
  window.PennGradient = {
    /**
     * Trigger the AI flash animation (like Google's AI Mode)
     * Both top and header by default
     * @param {number} delay - Optional delay in milliseconds before flash
     */
    flash: function(delay = 0) {
      this.flashBoth(delay);
    },

    /**
     * Trigger only the top flash animation
     * @param {number} delay - Optional delay in milliseconds before flash
     */
    flashTop: function(delay = 0) {
      setTimeout(() => {
        document.body.classList.remove('penn-gradient-pulse-top', 'penn-gradient-expand-top');
        document.body.classList.add('penn-gradient-flash-top');
        
        // Remove class after animation completes
        setTimeout(() => {
          document.body.classList.remove('penn-gradient-flash-top');
        }, 2000);
      }, delay);
    },

    /**
     * Trigger only the header border flash animation
     * @param {number} delay - Optional delay in milliseconds before flash
     */
    flashHeader: function(delay = 0) {
      setTimeout(() => {
        document.body.classList.add('penn-gradient-flash-header');
        
        // Remove class after animation completes
        setTimeout(() => {
          document.body.classList.remove('penn-gradient-flash-header');
        }, 2000);
      }, delay);
    },

    /**
     * Trigger both flashes with cascading effect
     * @param {number} delay - Optional delay in milliseconds before flash
     * @param {number} cascade - Delay between top and header (default 250ms)
     */
    flashBoth: function(delay = 0, cascade = 250) {
      this.flashTop(delay);
      this.flashHeader(delay + cascade);  // Header follows after cascade delay
    },
    
    /**
     * Trigger both flashes simultaneously (no cascade)
     * @param {number} delay - Optional delay in milliseconds before flash
     */
    flashSimultaneous: function(delay = 0) {
      this.flashTop(delay);
      this.flashHeader(delay);
    },

    /**
     * Trigger expand animation (iOS-style)
     */
    expand: function() {
      document.body.classList.remove('penn-gradient-flash', 'penn-gradient-pulse');
      document.body.classList.add('penn-gradient-expand');
      
      setTimeout(() => {
        document.body.classList.remove('penn-gradient-expand');
      }, 1800);
    },

    /**
     * Start continuous rotation (ambient AI mode)
     */
    startRotation: function() {
      document.body.classList.remove('penn-gradient-flash', 'penn-gradient-expand');
      document.body.classList.add('penn-gradient-pulse');
    },

    /**
     * Stop all animations
     */
    stop: function() {
      document.body.classList.remove('penn-gradient-flash', 'penn-gradient-pulse', 'penn-gradient-expand');
    },

    /**
     * Flash on specific element with action sweep effect
     * @param {HTMLElement|string} element - Element or selector
     */
    flashElement: function(element) {
      const el = typeof element === 'string' 
        ? document.querySelector(element) 
        : element;
      
      if (el) {
        el.classList.add('penn-action-flash');
        
        // Remove class after animation
        setTimeout(() => {
          el.classList.remove('penn-action-flash');
        }, 800);
      }
    },

    /**
     * Enable AI button effects globally
     */
    enableButtons: function() {
      document.body.classList.add('penn-ai-buttons-enabled');
      console.log('🎨 Penn AI button effects enabled');
    },

    /**
     * Disable AI button effects globally
     */
    disableButtons: function() {
      document.body.classList.remove('penn-ai-buttons-enabled');
      console.log('Penn AI button effects disabled');
    },

    /**
     * Toggle AI button effects
     */
    toggleButtons: function() {
      if (document.body.classList.contains('penn-ai-buttons-enabled')) {
        this.disableButtons();
      } else {
        this.enableButtons();
      }
    },

    /**
     * Add AI effect to specific button(s)
     * @param {string|HTMLElement|NodeList} selector - Button selector or element(s)
     */
    addToButton: function(selector) {
      const elements = typeof selector === 'string' 
        ? document.querySelectorAll(selector)
        : selector instanceof NodeList 
        ? selector 
        : [selector];
      
      elements.forEach(el => {
        el.classList.add('penn-ai-button');
        el.classList.remove('penn-ai-inactive');
      });
    },

    /**
     * Remove AI effect from specific button(s)
     * @param {string|HTMLElement|NodeList} selector - Button selector or element(s)
     */
    removeFromButton: function(selector) {
      const elements = typeof selector === 'string' 
        ? document.querySelectorAll(selector)
        : selector instanceof NodeList 
        ? selector 
        : [selector];
      
      elements.forEach(el => {
        el.classList.add('penn-ai-inactive');
      });
    },

    /**
     * Enable AI input/text field effects globally
     */
    enableInputs: function() {
      document.body.classList.add('penn-ai-inputs-enabled');
      console.log('🎨 Penn AI input effects enabled');
    },

    /**
     * Disable AI input effects globally
     */
    disableInputs: function() {
      document.body.classList.remove('penn-ai-inputs-enabled');
      console.log('Penn AI input effects disabled');
    },

    /**
     * Toggle AI input effects
     */
    toggleInputs: function() {
      if (document.body.classList.contains('penn-ai-inputs-enabled')) {
        this.disableInputs();
      } else {
        this.enableInputs();
      }
    },

    /**
     * Add AI effect to specific input(s) - wraps them if needed
     * @param {string|HTMLElement|NodeList} selector - Input selector or element(s)
     */
    addToInput: function(selector) {
      const elements = typeof selector === 'string' 
        ? document.querySelectorAll(selector)
        : selector instanceof NodeList 
        ? selector 
        : [selector];
      
      elements.forEach(input => {
        // For search input, use the existing parent
        if (input.id === 'gdoc-search-input' || input.classList.contains('gdoc-search__input')) {
          // Use existing parent container
          const parent = input.parentElement;
          parent.classList.add('penn-ai-input-wrapper');
          input.classList.add('penn-ai-input');
          parent.classList.remove('penn-ai-inactive');
        } else {
          // For other inputs, wrap them
          if (!input.parentElement.classList.contains('penn-ai-input-wrapper')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'penn-ai-input-wrapper';
            input.parentNode.insertBefore(wrapper, input);
            wrapper.appendChild(input);
          }
          input.classList.add('penn-ai-input');
          input.parentElement.classList.remove('penn-ai-inactive');
        }
      });
    },

    /**
     * Remove AI effect from specific input(s)
     * @param {string|HTMLElement|NodeList} selector - Input selector or element(s)
     */
    removeFromInput: function(selector) {
      const elements = typeof selector === 'string' 
        ? document.querySelectorAll(selector)
        : selector instanceof NodeList 
        ? selector 
        : [selector];
      
      elements.forEach(input => {
        if (input.parentElement.classList.contains('penn-ai-input-wrapper')) {
          input.parentElement.classList.add('penn-ai-inactive');
        }
      });
    }
  };

  // Set up backward compatibility - PennAI is now an alias for PennGradient
  window.PennAI = window.PennGradient;

  // Auto-flash on certain events (optional)
  document.addEventListener('DOMContentLoaded', function() {
    // Check for page-specific settings from frontmatter (via data attributes)
    const pageSettings = document.querySelector('meta[name="penn-gradient-settings"]');
    if (pageSettings) {
      // Parse settings - handle HTML entity encoding
      let content = pageSettings.getAttribute('content');
      // Decode HTML entities
      const textarea = document.createElement('textarea');
      textarea.innerHTML = content;
      content = textarea.value;
      
      const settings = JSON.parse(content || '{}');
      
      // Debug log to see what we got
      console.log('Penn Gradient settings loaded:', settings);
      
      // Enable buttons if specified (handle lowercase keys from Hugo)
      if (settings.enableButtons === true || settings.enablebuttons === true) {
        PennGradient.enableButtons();
        // Auto-add to any existing buttons
        const buttons = document.querySelectorAll('button, .gdoc-button');
        buttons.forEach(btn => PennGradient.addToButton(btn));
      }
      
      // Enable inputs if specified (handle lowercase keys from Hugo)
      if (settings.enableInputs === true || settings.enableinputs === true) {
        PennGradient.enableInputs();
        // Auto-add to search input if present
        const searchInput = document.getElementById('gdoc-search-input');
        if (searchInput) {
          PennGradient.addToInput('#gdoc-search-input');
        }
      }
      
      // Flash header on load if specified (handle lowercase keys from Hugo)
      if (settings.flashHeaderOnLoad === true || settings.flashheaderonload === true) {
        PennGradient.flashHeader(300);
      }
      
      // Full flash on load if specified (handle lowercase keys from Hugo)
      if (settings.flashOnLoad === true || settings.flashonload === true) {
        PennGradient.flash(300);
      }
    }
    
    // No legacy behavior - everything controlled by settings now

    // Flash on successful form submissions
    document.querySelectorAll('form').forEach(form => {
      form.addEventListener('submit', function(e) {
        // Only flash if form validates
        if (form.checkValidity()) {
          PennGradient.flash();
        }
      });
    });

    // Flash on edit button clicks
    document.querySelectorAll('.edit-link a').forEach(link => {
      link.addEventListener('click', function(e) {
        PennGradient.flash();
      });
    });

    // Keyboard shortcut for manual trigger (Ctrl/Cmd + Shift + G)
    document.addEventListener('keydown', function(e) {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'G') {
        e.preventDefault();
        PennGradient.flashBoth();
      }
    });

    // Add console message for developers
    console.log(
      '%c🎨 Penn Gradient Effects Ready!',
      'color: #011F5B; font-weight: bold; font-size: 14px;'
    );
    console.log(
      'Commands:\n' +
      '  === Flash Effects ===\n' +
      '  PennGradient.flash()             - Cascading flash (top → header)\n' +
      '  PennGradient.flashTop()          - Top gradient flash only\n' +
      '  PennGradient.flashHeader()       - Header border flash only\n' +
      '  PennGradient.flashBoth()         - Cascading flash (customizable delay)\n' +
      '  PennGradient.flashSimultaneous() - Both flashes at once\n' +
      '  \n' +
      '  === Input/Text Field Effects ===\n' +
      '  PennGradient.enableInputs()      - Enable gradient effect on all inputs\n' +
      '  PennGradient.disableInputs()     - Disable gradient effect on all inputs\n' +
      '  PennGradient.toggleInputs()      - Toggle input gradient effects\n' +
      '  PennGradient.addToInput("#search") - Add gradient to search field\n' +
      '  PennGradient.removeFromInput(s)  - Remove gradient from input(s)\n' +
      '  \n' +
      '  === Button Effects ===\n' +
      '  PennGradient.enableButtons()     - Enable gradient effect on all buttons\n' +
      '  PennGradient.disableButtons()    - Disable gradient effect on all buttons\n' +
      '  PennGradient.toggleButtons()     - Toggle button gradient effects\n' +
      '  PennGradient.addToButton(sel)    - Add gradient to specific button(s)\n' +
      '  PennGradient.removeFromButton(s) - Remove gradient from button(s)\n' +
      '  \n' +
      '  === Other Effects ===\n' +
      '  PennGradient.expand()            - iOS-style expansion\n' +
      '  PennGradient.startRotation()     - Continuous rotation\n' +
      '  PennGradient.stop()              - Stop all animations\n' +
      '  \n' +
      '  Keyboard: Ctrl/Cmd+Shift+G - Cascading flash'
    );
    
    // Quick start examples
    console.log(
      '%cQuick Start Examples:',
      'color: #019CDE; font-weight: bold;',
      '\n' +
      '1. Test on search field:\n' +
      '   PennGradient.enableInputs()\n' + 
      '   PennGradient.addToInput("#gdoc-search-input")\n' +
      '\n' +
      '2. Test on button:\n' +
      '   PennGradient.enableButtons()\n' +
      '   PennGradient.addToButton(".gdoc-button")\n'
    );
  });

  // Expose API for use in other scripts
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = window.PennAI;
  }
})();