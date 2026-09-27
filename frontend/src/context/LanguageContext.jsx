import { createContext, useCallback, useContext, useMemo, useState } from 'react';

const translations = {
  en: {
    // Header
    brandTitle: 'Federal Supreme Court Precedent Assistant',
    brandSubtitle: 'የሰበር ችሎት የሕግ ትርጉም ረዳት',
    switchLang: 'ወደ አማርኛ ቀይር',

    // Home
    courtChip: 'Federal Supreme Court of Ethiopia • Cassation Bench',
    heroTitle: 'Find binding precedent in seconds, not hours',
    heroSubtitle: 'አስገዳጅ የሰበር የሕግ ትርጉሞችን በቅጽበት ይፈልጉ',
    heroDescription:
      'Assisting Federal Judges and legal researchers in searching binding Cassation Division rulings to ensure faster, more consistent judicial outcomes across all jurisdictions.',
    startChat: 'Start Chat →',
    volumes: 'Volumes 15–21 Indexed',
    holdings: 'Over 4,800+ Binding Legal Principles',
    citations: 'Verified Gazette Citations',

    pillar1Title: 'Natural Language Legal Query',
    pillar1Text:
      'Search by facts, contract clauses, or procedural issues in plain Amharic or English without complex syntax codes.',
    pillar1Foot: 'Amharic & English Semantics',
    pillar2Title: 'Strictly Sourced to Docket',
    pillar2Text:
      'Every synthesized answer is anchored to verified File Number (መ.ቁ), bench composition, volume, and sitting date.',
    pillar2Foot: 'Proclamation No. 454/2005 Verified',
    pillar3Title: 'Non-Binding Dicta Filtered',
    pillar3Text:
      'Strict isolation of controlling ratio decidendi from non-binding obiter dictum across all regional appeals.',
    pillar3Foot: 'Judicial Weight Verification',

    disclaimer:
      'Official Judicial Research Tool — Strictly for authorized research purposes and not a substitute for independent judicial evaluation.',

    // Chat
    newInquiry: 'New Inquiry',
    searchHistory: 'Search docket history…',
    today: 'Today',
    yesterday: 'Yesterday',
    previous: 'Previous 7 Days',
    chamberTitle: 'Hon. Justice Chamber',
    chamberSub: 'Federal Supreme Court',
    archivedDockets: 'Archived Dockets',
    volumeIndex: 'Volume Index',

    integrityTitle: 'Cassation Division Precedent Engine',
    integrityTag: 'Proclamation 1234/2021 Art. 2(1)',
    integrityDesc:
      'Interpretations rendered by the Federal Supreme Court Cassation Division with five or more judges are legally binding on all federal and regional courts.',

    emptyChat: 'A new inquiry is ready. Enter your legal research question below.',
    searching: 'Searching the precedent register…',
    step1: 'Analyzing query legal concepts & case references…',
    step2: 'Searching Cassation precedent vector database & gazette register…',
    step3: 'Extracting ratio decidendi & binding holdings…',
    step4: 'Synthesizing judicial opinion response…',
    searchLang: 'Search language: English',
    volumeFilter: 'Volume Filter: Volumes 15–21',
    send: 'Send',
    sendingLabel: 'Processing…',

    // Assistant
    assistantLabel: 'FSC Judicial Precedent Retrieval',
    retrievedLabel: 'Synthesized Legal Opinion & Findings',
    toggleCitations: 'Show Cited Precedent Sources',
    hideCitations: 'Hide Cited Precedent Sources',
    showingCitations: 'Precedent Sources & Gazette Dossiers',
    noResults: 'No source-backed results are available for this inquiry.',
    noCitations: 'No cited cassation decisions were returned.',
    rankedPrecedent: 'Ranked precedent',
    sourceHolding: 'Source-linked holding',
    saveDossier: '⊕ Save to Case Dossier',
    savedDossier: '✓ Saved to Case Dossier',
    verifyLabel: 'Verify against official FSC reporter',
    court: 'Court',
    cassFileNo: 'Cassation File No.',
    dateNotAvailable: 'Date not available in source metadata',
    match: 'match',
    cassationDivision: 'Cassation Division',

    composerPlaceholder:
      'Ask about a case, binding ruling, or legal question in English…',
    homeComposerPlaceholder:
      'e.g. ውል ማፍረስ ወይም የይርጋ ጊዜ መቋረጥ (or Cass. File No. 182941)...',
    inquire: 'Inquire',

    noHistory: 'No conversations yet',
  },
  am: {
    brandTitle: 'የፌዴራል ጠቅላይ ፍ/ቤት የሰበር ረዳት',
    brandSubtitle: 'Federal Supreme Court Precedent Assistant',
    switchLang: 'Switch to English',

    courtChip: 'የኢትዮጵያ ፌዴራል ጠቅላይ ፍርድ ቤት • የሰበር ችሎት',
    heroTitle: 'የፋዳራሌ ጠቅሊይ ፌ/ቤት ሰበር ችልት ውሣኔዎችን በቅጽበት ያግኙ',
    heroSubtitle: 'Find binding precedent in seconds, not hours',
    heroDescription:
      'ለፌዴራል ዳኞች እና የሕግ ተመራማሪዎች አስገዳጅ የሰበር ውሳኔዎችን በፍጥነት ለማግኘት የተቀናጀ መረጃ ሥርዓት።',
    startChat: 'ውይይት ይጀምሩ →',
    volumes: 'ቅጽ 15–21 ተደራጅተዋል',
    holdings: 'ከ4,800 በላይ አስገዳጅ የሕግ መርሆዎች',
    citations: 'የተረጋገጡ የጋዜጣ ጥቅሶች',

    pillar1Title: 'በተፈጥሮ ቋንቋ የሕግ ፍለጋ',
    pillar1Text:
      'በቀላል አማርኛ ወይም እንግሊዝኛ ያልተወሳሰበ ሥነ-ሥርዓት ሳይፈልግ በሕግ ጥያቄዎች ይፈልጉ።',
    pillar1Foot: 'የአማርኛ እና እንግሊዝኛ ትርጉም',
    pillar2Title: 'ከመዝገብ ቁጥር ጋር የተረጋገጠ',
    pillar2Text:
      'እያንዳንዱ ምላሽ ከተረጋገጠ መ/ቁ፣ ችሎት ስብጥር፣ ቅጽ እና ቀን ጋር ተያይዟል።',
    pillar2Foot: 'አዋጅ ቁ. 454/2005 ማረጋገጫ',
    pillar3Title: 'አስገዳጅ ያልሆኑ ንግግሮች ተለይተዋል',
    pillar3Text:
      'አስገዳጅ ratio decidendi ከobiter dictum ተለይቶ ቀርቧል።',
    pillar3Foot: 'የዳኝነት ክብደት ማረጋገጫ',

    disclaimer:
      'ይፋዊ የዳኝነት ምርምር መሣሪያ — ለተፈቀደ ምርምር ብቻ የሚያገለግል ሲሆን ነፃ የፍርድ ግምገማን አይተካም።',

    newInquiry: 'አዲስ ምክክር',
    searchHistory: 'የመዝገብ ታሪክ ፈልግ…',
    today: 'ዛሬ',
    yesterday: 'ትላንት',
    previous: 'ያለፉት 7 ቀናት',
    chamberTitle: 'ክቡር ዳኛ ክፍል',
    chamberSub: 'ፌዴራል ጠቅላይ ፍርድ ቤት',
    archivedDockets: 'የተመዘገቡ መዛግብት',
    volumeIndex: 'ቅጽ ማውጫ',

    integrityTitle: 'የሰበር ችሎት የውሳኔ ሞተር',
    integrityTag: 'አዋጅ 1234/2021 አንቀጽ 2(1)',
    integrityDesc:
      'በፌዴራል ጠቅላይ ፍ/ቤት የሰበር ችሎት አምስት ወይም ከዚያ በላይ ዳኞች የተሰጡ የሕግ ትርጉሞች በሁሉም ፌዴራል እና ክልል ፍ/ቤቶች ላይ አስገዳጅ ናቸው።',

    emptyChat: 'አዲስ ምክክር ተጀምሯል። ጥያቄዎን ከታች ያስገቡ።',
    searching: 'የሰበር ውሳኔ መዝገብ ፍለጋ ላይ…',
    step1: 'የሕግ ጽንሰ-ሐሳቦች እና የመዝገብ ቁጥሮች በመተንተን ላይ…',
    step2: 'የሰበር መዛግብት የቬክተር ዳታቤዝ እና የጋዜጣ መዝገብ በመፈለግ ላይ…',
    step3: 'አስገዳጅ የሕግ ትርጉሞች (ratio decidendi) በመለየት ላይ…',
    step4: 'የዳኝነት ሕጋዊ ምላሽ በማዘጋጀት ላይ…',
    searchLang: 'የፍለጋ ቋንቋ፦ አማርኛ',
    volumeFilter: 'ቅጽ ማጣሪያ፦ ቅጽ 15–21',
    send: 'ላክ',
    sendingLabel: 'በማዘጋጀት ላይ…',

    assistantLabel: 'የፌ/ጠ/ፍ/ቤት ሰበር ውሳኔ',
    retrievedLabel: 'የተቀናጀ የሕግ ውሳኔ እና ማጠቃለያ',
    toggleCitations: 'የተጠቀሱ የሰበር ውሳኔ መዛግብትን አሳይ',
    hideCitations: 'የተጠቀሱ የሰበር ውሳኔ መዛግብትን ደብቅ',
    showingCitations: 'የተጠቀሱ የምንጭ መዛግብት',
    noResults: 'ለዚህ ጥያቄ ምንም ተዛማጅ ውሳኔ አልተገኘም።',
    noCitations: 'ምንም ጥቅስ ያለው ውሳኔ አልተመለሰም።',
    rankedPrecedent: 'ደረጃ የተሰጠው ውሳኔ',
    sourceHolding: 'ከምንጭ ጋር የተያያዘ ይዞታ',
    saveDossier: '⊕ ወደ መዝገብ አስቀምጥ',
    savedDossier: '✓ ተቀምጧል',
    verifyLabel: 'በይፋዊ ሪፖርተር ያረጋግጡ',
    court: 'ፍርድ ቤት',
    cassFileNo: 'የሰበር መ/ቁ',
    dateNotAvailable: 'ቀን በምንጭ ውስጥ የለም',
    match: 'ተዛማጅ',
    cassationDivision: 'የሰበር ችሎት',

    composerPlaceholder:
      'ስለ ጉዳይ፣ አስገዳጅ ውሳኔ ወይም የሕግ ጥያቄ በአማርኛ ይጠይቁ…',
    homeComposerPlaceholder:
      'ለምሳሌ፦ ውል ማፍረስ ወይም የይርጋ ጊዜ መቋረጥ (ወይም መ/ቁ 182941)...',
    inquire: 'ፈልግ',

    noHistory: 'ገና ውይይት የለም',
  },
};

const LanguageContext = createContext(undefined);

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState('en');

  const toggleLanguage = useCallback(() => {
    setLanguage((prev) => (prev === 'en' ? 'am' : 'en'));
  }, []);

  const t = useMemo(() => translations[language], [language]);

  const value = useMemo(
    () => ({ language, toggleLanguage, t }),
    [language, toggleLanguage, t],
  );

  return (
    <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error('useLanguage must be inside LanguageProvider');
  return ctx;
}
