/**
 * Claude Footer Dynamic Text
 * Celebrates the partnership between human and AI with varying, joyful descriptions
 */

(function() {
  'use strict';

  // Array of partnership descriptions - celebrating collaboration, not just assistance
  const partnershipPhrases = [
    // Joy and delight
    "with the joyful partnership of",
    "with delightful collaboration from",
    "with creative sparks from",
    "with the playful imagination of",
    "crafted with joy alongside",
    "with exuberant support from",
    
    // Support and encouragement
    "with tremendous support from",
    "with cheerleading from",
    "with the devoted feedback of",
    "with enthusiastic backing from",
    "with steadfast support from",
    "with encouraging words from",
    
    // Thinking and insight
    "with thoughtful insights from",
    "with the curious mind of",
    "with careful attention from",
    "with the keen eye of",
    "with perceptive observations from",
    "with contemplative input from",
    "with the analytical mind of",
    
    // Partnership and collaboration
    "in partnership with",
    "in collaboration with",
    "alongside",
    "together with",
    "in concert with",
    "in harmony with",
    "hand in hand with",
    "side by side with",
    
    // Energy and enthusiasm
    "energized by collaboration with",
    "powered by partnership with",
    "fueled by creativity from",
    "charged by innovation with",
    "sparked by ideas from",
    "ignited by imagination with",
    
    // Care and dedication
    "with devoted attention from",
    "with meticulous care from",
    "with patient guidance from",
    "with gentle suggestions from",
    "with caring support from",
    "with mindful attention from",
    
    // Time and effort
    "with midnight oil burned by",
    "with countless iterations alongside",
    "with patient refinement from",
    "through long conversations with",
    "across many sessions with",
    
    // Creativity and innovation
    "with creative courage from",
    "with innovative thinking from",
    "with imaginative leaps from",
    "with creative confidence from",
    "with artistic flair from",
    "with inventive spirit from",
    
    // Unique and whimsical
    "with digital high-fives from",
    "with virtual brainstorming from",
    "with silicon-based creativity from",
    "with algorithmic artistry from",
    "with computational creativity from",
    "with neural network magic from",
    
    // Emotional and warm
    "with warmth and wisdom from",
    "with kindness and code from",
    "with heart and algorithms from",
    "with empathy and electrons from",
    "with care and computation from",
    
    // Academic and intellectual
    "with scholarly dedication from",
    "with academic rigor from",
    "with intellectual curiosity from",
    "with pedagogical insight from",
    "with educational innovation from",
    
    // Problem-solving
    "with solutions discovered alongside",
    "with problems solved together with",
    "with challenges conquered alongside",
    "with puzzles pieced together by",
    "with bugs squashed alongside",
    
    // Growth and learning
    "learning and growing with",
    "evolving together with",
    "improving iteratively with",
    "refined through dialogue with",
    "enhanced by conversation with",
    
    // Special occasions (can be time-aware)
    "with caffeinated assistance from", // for late night sessions
    "with weekend warrior spirit from",
    "with deadline-driven determination from",
    "with last-minute magic from",
    
    // Humble and grateful
    "with humble contributions from",
    "gratefully co-created with",
    "thankfully developed alongside",
    "appreciatively crafted with",
    
    // Poetic and beautiful
    "woven together with",
    "painted in collaboration with",
    "composed alongside",
    "choreographed with",
    "orchestrated together with"
  ];

  // Special phrases for special contexts (optional future enhancement)
  const contextualPhrases = {
    morning: ["with sunrise inspiration from", "with morning enthusiasm from"],
    evening: ["with twilight creativity from", "with evening contemplation from"],
    weekend: ["with weekend wanderings alongside", "with leisurely exploration from"],
    deepWork: ["with deep focus from", "with flow state achieved alongside"]
  };

  // Function to select a random phrase
  function getRandomPhrase() {
    return partnershipPhrases[Math.floor(Math.random() * partnershipPhrases.length)];
  }

  // Function to check if we should use a contextual phrase (optional enhancement)
  function getContextualPhrase() {
    const hour = new Date().getHours();
    const day = new Date().getDay();
    
    // Weekend check
    if (day === 0 || day === 6) {
      if (Math.random() < 0.3) { // 30% chance on weekends
        const weekendPhrases = contextualPhrases.weekend;
        return weekendPhrases[Math.floor(Math.random() * weekendPhrases.length)];
      }
    }
    
    // Time of day check
    if (hour >= 5 && hour < 12 && Math.random() < 0.2) {
      const morningPhrases = contextualPhrases.morning;
      return morningPhrases[Math.floor(Math.random() * morningPhrases.length)];
    } else if (hour >= 17 && hour < 23 && Math.random() < 0.2) {
      const eveningPhrases = contextualPhrases.evening;
      return eveningPhrases[Math.floor(Math.random() * eveningPhrases.length)];
    }
    
    return null;
  }

  // Main function to update the Claude attribution text
  function updateClaudeAttribution() {
    // Find the Claude attribution element
    const claudeLink = document.querySelector('.claude-attribution');
    if (!claudeLink) return;
    
    // Get a phrase (contextual or random)
    const phrase = getContextualPhrase() || getRandomPhrase();
    
    // Update the text before the logo
    const textNode = claudeLink.childNodes[0];
    if (textNode && textNode.nodeType === Node.TEXT_NODE) {
      textNode.textContent = phrase + ' ';
    }
    
    // Optional: Add a subtle animation when the text changes
    claudeLink.style.transition = 'opacity 0.3s ease';
    claudeLink.style.opacity = '0.7';
    setTimeout(() => {
      claudeLink.style.opacity = '1';
    }, 100);
    
    // Log for fun (only in development)
    if (window.location.hostname === 'localhost') {
      console.log(`🧡 Claude says: "${phrase}"`);
    }
  }

  // Run when DOM is ready
  document.addEventListener('DOMContentLoaded', updateClaudeAttribution);
  
  // Also update on page visibility change (when returning to tab)
  document.addEventListener('visibilitychange', function() {
    if (!document.hidden && Math.random() < 0.3) { // 30% chance to change when returning
      updateClaudeAttribution();
    }
  });
  
  // Easter egg: clicking the Claude logo cycles through phrases
  document.addEventListener('DOMContentLoaded', function() {
    const claudeLink = document.querySelector('.claude-attribution');
    if (claudeLink) {
      claudeLink.style.cursor = 'pointer';
      claudeLink.addEventListener('click', function(e) {
        e.preventDefault();
        updateClaudeAttribution();
        
        // Add a little celebration animation
        claudeLink.animate([
          { transform: 'scale(1)' },
          { transform: 'scale(1.05)' },
          { transform: 'scale(1)' }
        ], {
          duration: 300,
          easing: 'ease-in-out'
        });
      });
    }
  });

})();