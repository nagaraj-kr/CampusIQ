import { fetchRecommendations, resolveCoords } from './api.js';

const QUESTIONS = [
  {
    key: 'cutoff',
    ask: "👋 Welcome! I'm **CampusIQ**, your AI college advisor.\n\nLet's find your perfect college. What's your **cutoff score**?\n\n*(e.g., 85, 92.5 — for HSC/TNEA cutoff)*",
    validate: (v) => !isNaN(parseFloat(v)) && parseFloat(v) >= 0 && parseFloat(v) <= 200,
    parse: (v) => parseFloat(v),
    error: "Please enter a valid cutoff score (e.g., 85 or 92.5).",
  },
  {
    key: 'course',
    ask: "Great score! Now, which **course** are you targeting?\n\n*(e.g., Computer Science Engineering, Mechanical Engineering, MBA, BCA...)*",
    validate: (v) => v.trim().length > 1,
    parse: (v) => v.trim(),
    error: "Please enter a valid course name.",
  },
  {
    key: 'budget',
    ask: "What's your **annual fee budget**? *(in ₹)*\n\nType a number like **150000** for ₹1.5 Lakh or **500000** for ₹5 Lakh.",
    validate: (v) => !isNaN(parseInt(v.replace(/,/g, ''))) && parseInt(v.replace(/,/g, '')) > 0,
    parse: (v) => parseInt(v.replace(/,/g, '')),
    error: "Please enter a valid amount (e.g., 200000 for ₹2 Lakh).",
  },
  {
    key: 'location',
    ask: "Which **city or district** are you from?\n\nThis helps me prioritise colleges closer to you.\n*(e.g., Chennai, Madurai, Coimbatore, Trichy...)*",
    validate: (v) => v.trim().length > 1,
    parse: (v) => v.trim(),
    error: "Please enter your city or district.",
  },
];

export { QUESTIONS };

export async function generateBotResponse(userInput, currentStep, studentData) {
  if (currentStep >= QUESTIONS.length) {
    return handleFollowUp(userInput, studentData);
  }

  const currentQ = QUESTIONS[currentStep];

  if (!currentQ.validate(userInput)) {
    return {
      reply: `⚠️ ${currentQ.error}\n\n${currentQ.ask}`,
      nextStep: currentStep,
      updatedData: studentData,
      isFetching: false,
    };
  }

  const parsedValue = currentQ.parse(userInput);
  const updatedData = { ...studentData, [currentQ.key]: parsedValue };

  if (currentStep === QUESTIONS.length - 1) {
    const summary = buildSummary(updatedData);
    return {
      reply: `✅ Got it! Here's your profile:\n\n${summary}\n\n🔍 **Fetching your college recommendations...**\nOur AI engine is crunching placement data, fees, and distance — just a moment!`,
      nextStep: currentStep + 1,
      updatedData,
      isFetching: true,
    };
  }

  return {
    reply: QUESTIONS[currentStep + 1].ask,
    nextStep: currentStep + 1,
    updatedData,
    isFetching: false,
  };
}

export function buildResultMessage(colleges) {
  if (!colleges || colleges.length === 0) {
    return "😔 No colleges matched your profile exactly. Try **widening your budget** or **adjusting your cutoff**.\n\nType **restart** to search again!";
  }

  let msg = `🎓 **Top ${colleges.length} College${colleges.length > 1 ? 's' : ''} for You**\n\n`;

  colleges.forEach((c, i) => {
    const rank = i === 0 ? '🥇' : (i === 1 ? '🥈' : '🥉');
    // Handle both distance and distance_km field names
    const distance = c.distance_km || c.distance;
    const dist = distance ? ` · 📍 ${Math.round(distance)} km away` : '';
    const placement = c.placement_percentage ? ` · 📈 ${c.placement_percentage}% placement` : '';
    const fees = c.fees ? ` · 💰 ₹${Number(c.fees).toLocaleString('en-IN')}/yr` : '';
    const cutoff = c.cutoff ? ` · ✂️ Cutoff: ${c.cutoff}` : '';
    const score = c.score ? ` · ⭐ Score: ${c.score}/100` : '';

    msg += `${rank} **${c.college_name || c.name}**\n`;
    msg += `${c.location || ''}${dist}${score}\n\n`;
    
    msg += `📚 ${c.course_name || c.course}${fees}${cutoff}${placement}\n`;

    // Add website link if available
    console.log(`College ${i}: website =`, c.website);
    if (c.website) {
      const linkMarkdown = `🌐 [Visit Official Website](${c.website})\n`;
      console.log('Adding link markdown:', linkMarkdown);
      msg += linkMarkdown;
    }

    if (c.ai_reasoning) {
      if (c.ai_reasoning.summary) msg += `\n💡 *${c.ai_reasoning.summary}*\n`;
      if (c.ai_reasoning.pros?.length) {
        msg += `\n✅ **Pros:** ${c.ai_reasoning.pros.slice(0, 2).join(' · ')}\n`;
      }
      if (c.ai_reasoning.cons?.length) {
        msg += `⚠️ **Cons:** ${c.ai_reasoning.cons.slice(0, 1).join(' · ')}\n`;
      }
      if (c.ai_reasoning.verdict) msg += `\n📝 *${c.ai_reasoning.verdict}*\n`;
    }

    if (i < colleges.length - 1) msg += '\n---\n\n';
  });

  msg += "\n\nAsk me about **placements**, **fees**, or type **restart** to search again!";
  
  console.log('Final message includes images:', msg.includes('!['));
  console.log('Final message sample:', msg.substring(0, 300));
  
  return msg;
}

export function buildErrorMessage(err) {
  return `❌ **Couldn't fetch recommendations right now.**\n\n${err?.message || 'The server may be offline.'}\n\nMake sure your Django backend is running at \`localhost:8000\`.\n\nType **restart** to try again.`;
}

function handleFollowUp(input, studentData) {
  const lower = input.toLowerCase();

  if (lower.includes('restart') || lower.includes('start over') || lower.includes('reset')) {
    return { reply: "🔄 Let's start fresh!\n\n" + QUESTIONS[0].ask, nextStep: 0, updatedData: {}, isFetching: false };
  }
  if (lower.includes('placement') || lower.includes('job')) {
    return { reply: "📈 **Placement Rates**: Colleges are scored on placement %. Top TN engineering colleges typically report 80–95% for CS/IT branches.\n\nType **restart** to run a new search!", nextStep: QUESTIONS.length, updatedData: studentData, isFetching: false };
  }
  if (lower.includes('fee') || lower.includes('cost') || lower.includes('budget')) {
    const b = studentData.budget ? `₹${Number(studentData.budget).toLocaleString('en-IN')}/year` : 'your set budget';
    return { reply: `💰 Your budget was **${b}**. The engine filters and scores colleges within this range.\n\nType **restart** to try a different budget!`, nextStep: QUESTIONS.length, updatedData: studentData, isFetching: false };
  }

  if (lower.includes('distance') || lower.includes('near')) {
    return { reply: `📍 Distance was calculated via the **Haversine formula** from **${studentData.location || 'your location'}**. Closer colleges score higher (max 500 km range).\n\nType **restart** to search again!`, nextStep: QUESTIONS.length, updatedData: studentData, isFetching: false };
  }

  return {
    reply: "I've already found your best matches! 🎓\n\nAsk about **placements**, **fees**, **hostel**, **distance** — or type **restart** to search with a new profile.",
    nextStep: QUESTIONS.length,
    updatedData: studentData,
    isFetching: false,
  };
}

function buildSummary(data) {
  const lines = [];
  if (data.cutoff !== undefined) lines.push(`📊 **Cutoff**: ${data.cutoff}`);
  if (data.course) lines.push(`📚 **Course**: ${data.course}`);
  if (data.budget) lines.push(`💰 **Budget**: ₹${Number(data.budget).toLocaleString('en-IN')}/year`);
  if (data.location) lines.push(`📍 **Location**: ${data.location}`);
  if (data.hostel !== undefined) lines.push(`🏠 **Hostel**: ${data.hostel ? 'Yes' : 'No'}`);
  return lines.join('\n');
}
