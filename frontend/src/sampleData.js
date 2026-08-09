// Generates 250 realistic sample sales emails covering all routing categories.

const NAMES = [
  "Priya Sharma",
  "Rahul Verma",
  "Anita Desai",
  "Vikram Singh",
  "Neha Gupta",
  "Arjun Patel",
  "Sneha Reddy",
  "Karan Malhotra",
  "Divya Iyer",
  "Amit Joshi",
  "Pooja Nair",
  "Rohan Mehta",
  "Kavya Krishnan",
  "Suresh Kumar",
  "Meera Pillai",
  "Rajesh Khanna",
  "Sunita Rao",
  "Deepak Agarwal",
  "Nisha Bansal",
  "Sanjay Tiwari",
];

const COMPANIES = [
  "TechnoSolutions Pvt Ltd",
  "Galaxy Enterprises",
  "Vertex Systems",
  "BlueSky Corp",
  "NexGen Industries",
  "Orion Technologies",
  "Summit Group",
  "Prime Infotech",
  "Apex Solutions",
  "Innovate Labs",
  "Meridian Corp",
  "Quantum Systems",
];

function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}
function uid() {
  return "e-" + Math.random().toString(36).slice(2, 10);
}

function enterpriseRfp(i) {
  const value = Math.floor(Math.random() * 9 + 2) * 1000000; // 2-10 cr
  const company = pick(COMPANIES);
  return {
    email_id: uid(),
    thread_id: "thr-" + i,
    from_name: pick(NAMES),
    from_email:
      "procurement@" + company.toLowerCase().replace(/[^a-z]/g, "") + ".com",
    subject: `Request for Proposal - ${company} - Enterprise License`,
    body: `Dear Team,\n\nWe at ${company} are seeking proposals for a company-wide deployment of your sales platform. Attached is our RFP document. The estimated deal value is Rs ${value.toLocaleString(
      "en-IN"
    )}. We request a demo and pricing within 2 weeks.\n\nDeadline for submission: within 72 hours.\n\nRegards,\n${pick(
      NAMES
    )}\nProcurement Head`,
    received_at: new Date().toISOString(),
    is_reply: false,
  };
}

function smbDemo(i) {
  const company = pick(COMPANIES);
  return {
    email_id: uid(),
    thread_id: "thr-" + i,
    from_name: pick(NAMES),
    from_email:
      "hello@" + company.toLowerCase().replace(/[^a-z]/g, "") + ".com",
    subject: "Product Demo Request",
    body: `Hi,\n\nWe are a growing small business and are interested in a product demo. Could you share pricing for a 10-seat subscription? We'd like to evaluate your solution for our team.\n\nThanks,\n${pick(
      NAMES
    )}`,
    received_at: new Date().toISOString(),
    is_reply: false,
  };
}

function govTender(i) {
  return {
    email_id: uid(),
    thread_id: "thr-" + i,
    from_name: pick(NAMES),
    from_email:
      "tenders@" + pick(["govt", "psu", "ministry"]).toLowerCase() + ".in",
    subject: "Expression of Interest - Government Tender",
    body: `Dear Sir/Madam,\n\nThis is regarding a government tender for digital solutions. We are inviting bids from eligible vendors. The estimated value is Rs 5,00,000. Interested parties should submit their proposal.\n\nRegards,\nTender Cell`,
    received_at: new Date().toISOString(),
    is_reply: false,
  };
}

function marketing(i) {
  return {
    email_id: uid(),
    thread_id: "thr-" + i,
    from_name: pick(NAMES),
    from_email:
      "events@" +
      pick(COMPANIES)
        .toLowerCase()
        .replace(/[^a-z]/g, "") +
      ".com",
    subject: "Sponsorship Opportunity - Tech Conference",
    body: `Hello,\n\nWe are organizing a major tech conference and would like to propose a sponsorship and co-marketing partnership. This is a great PR opportunity to reach our audience.\n\nLet's discuss.\n\n${pick(
      NAMES
    )}`,
    received_at: new Date().toISOString(),
    is_reply: false,
  };
}

function finance(i) {
  return {
    email_id: uid(),
    thread_id: "thr-" + i,
    from_name: pick(NAMES),
    from_email:
      "accounts@" +
      pick(COMPANIES)
        .toLowerCase()
        .replace(/[^a-z]/g, "") +
      ".com",
    subject: "Invoice #" + (1000 + i) + " - Payment Due",
    body: `Hi,\n\nPlease find attached invoice #${
      1000 + i
    } for the recent services rendered. This is a payment reminder. Please arrange the payment at the earliest. GST details included.\n\nAccounts Team`,
    received_at: new Date().toISOString(),
    is_reply: false,
  };
}

function alliance(i) {
  return {
    email_id: uid(),
    thread_id: "thr-" + i,
    from_name: pick(NAMES),
    from_email:
      "partners@" +
      pick(COMPANIES)
        .toLowerCase()
        .replace(/[^a-z]/g, "") +
      ".com",
    subject: "Channel Partnership Proposal",
    body: `Hello,\n\nWe would like to discuss a reseller and channel partnership. We are interested in integrating your API and co-selling with you. Please share your partner program details.\n\nBest,\n${pick(
      NAMES
    )}`,
    received_at: new Date().toISOString(),
    is_reply: false,
  };
}

function ooo(i) {
  return {
    email_id: uid(),
    thread_id: "thr-" + i,
    from_name: pick(NAMES),
    from_email:
      "hr@" +
      pick(COMPANIES)
        .toLowerCase()
        .replace(/[^a-z]/g, "") +
      ".com",
    subject: "Out of Office - Automatic Reply",
    body: `Thank you for your email. I am currently out of the office and will be back next Monday. For urgent matters, please contact my colleague. This is an automated reply.`,
    received_at: new Date().toISOString(),
    is_reply: false,
  };
}

function newsletter(i) {
  return {
    email_id: uid(),
    thread_id: "thr-" + i,
    from_name: "Marketing Team",
    from_email:
      "newsletter@" +
      pick(COMPANIES)
        .toLowerCase()
        .replace(/[^a-z]/g, "") +
      ".com",
    subject: "Your Weekly Product Newsletter",
    body: `Hi there,\n\nHere is this week's digest of product updates, tips, and industry insights. If you no longer wish to receive these emails, please unsubscribe using the link below.`,
    received_at: new Date().toISOString(),
    is_reply: false,
  };
}

function vendorSpam(i) {
  return {
    email_id: uid(),
    thread_id: "thr-" + i,
    from_name: pick(NAMES),
    from_email:
      "seo@" + pick(["topseo", "rankmax", "seopro"]).toLowerCase() + ".com",
    subject: "Improve Your SEO Rankings",
    body: `Hi,\n\nWe can help improve your website rankings with our SEO and backlink building services. Boost your web traffic and digital marketing today. Contact us for a free audit.`,
    received_at: new Date().toISOString(),
    is_reply: false,
  };
}

function hinglish(i) {
  return {
    email_id: uid(),
    thread_id: "thr-" + i,
    from_name: pick(NAMES),
    from_email:
      "info@" +
      pick(COMPANIES)
        .toLowerCase()
        .replace(/[^a-z]/g, "") +
      ".com",
    subject: "Product ke baare mein jaankari",
    body: `Namaste,\n\nHum aapke product mein ruchi rakh rahe hain. Kya aap demo de sakte hain? Humari company choti hai, budget around 3 lakh hai. Please pricing bhejein.`,
    received_at: new Date().toISOString(),
    is_reply: false,
  };
}

function ambiguous(i) {
  return {
    email_id: uid(),
    thread_id: "thr-" + i,
    from_name: pick(NAMES),
    from_email:
      pick(NAMES).split(" ")[0].toLowerCase() +
      "@" +
      pick(COMPANIES)
        .toLowerCase()
        .replace(/[^a-z]/g, "") +
      ".com",
    subject: "General Business Inquiry",
    body: `Hello,\n\nI have a general inquiry about your company and would like to know more about what you offer. Looking forward to your response.\n\n${pick(
      NAMES
    )}`,
    received_at: new Date().toISOString(),
    is_reply: false,
  };
}

function deadlineUrgent(i) {
  return {
    email_id: uid(),
    thread_id: "thr-" + i,
    from_name: pick(NAMES),
    from_email:
      "buyer@" +
      pick(COMPANIES)
        .toLowerCase()
        .replace(/[^a-z]/g, "") +
      ".com",
    subject: "URGENT - Tender response needed",
    body: `Dear Sir,\n\nThis is a Request for Proposal from a government department. The deal value is Rs 1.5 crore. We need a response within 48 hours. Please prioritize this.\n\nRegards,\n${pick(
      NAMES
    )}`,
    received_at: new Date().toISOString(),
    is_reply: false,
  };
}

export function generateSamples(count = 250) {
  const emails = [];
  const generators = [
    enterpriseRfp,
    smbDemo,
    govTender,
    marketing,
    finance,
    alliance,
    ooo,
    newsletter,
    vendorSpam,
    hinglish,
    ambiguous,
    deadlineUrgent,
  ];
  for (let i = 0; i < count; i++) {
    const gen = generators[i % generators.length];
    emails.push(gen(i));
  }
  return emails;
}
