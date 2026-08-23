(function () {
  "use strict";

  const languages = [
    {code: "en", label: "English"},
    {code: "sn", label: "ChiShona"},
    {code: "nd", label: "isiNdebele"},
    {code: "sw", label: "Kiswahili"},
    {code: "zu", label: "isiZulu"}
  ];

  const en = {
    language_label: "Language",
    hero_eyebrow: "SIMBA AUTONOMOUS ENERGY OPERATIONS AGENT",
    hero_title: "Set the energy goal. Inspect the plan. Keep the operator in control.",
    hero_description: "The agent observes configured facilities, forecasts demand, ranks safe non-critical actions, requests approval, executes only in the software plant, verifies the result and replans when needed.",
    runtime_checking: "Checking agent runtime",
    software_only: "Software-in-the-loop only",
    live_disabled: "Live electrical switching is disabled.",
    firewall: "DETERMINISTIC ENERGY SAFETY FIREWALL",
    firewall_description: "Critical loads, stale commands and unavailable devices are blocked before execution.",
    boundary_default: "Approval is required. Replanning stays inside the approved mission limits.",
    process_heading: "What the agent does",
    process_description: "A bounded, auditable loop turns an energy target into a verified software-only response.",
    observe: "Observe",
    observe_detail: "Read every configured facility and data-freshness flag.",
    forecast: "Forecast",
    forecast_detail: "Estimate campus demand and detect a limit breach.",
    plan_safely: "Plan safely",
    plan_detail: "Rank flexible loads after deterministic safety checks.",
    approve: "Approve",
    approve_detail: "Let the operator approve, modify, reject or set limits.",
    emulate: "Emulate",
    emulate_detail: "Apply actions only to the software plant.",
    verify_replan: "Verify and replan",
    verify_detail: "Measure the response and adapt when reality differs.",
    mission_heading: "Campus peak mission",
    goal_default: "Keep campus demand below the configured limit during the target window without touching critical loads.",
    complication_label: "Resilience test",
    device_unavailable: "Device unavailable",
    underperforming_action: "Action underperforms",
    prepare_mission: "Prepare mission",
    run_demo: "Run resilient demo",
    refresh: "Refresh",
    empty_start: "Start a mission to observe, plan, approve, execute and verify.",
    approval_heading: "Mission and approval",
    approval_description: "Approve, modify, reject or approve with explicit limits",
    no_mission: "No mission has been prepared in this runtime.",
    events_heading: "Agent event trail",
    events_description: "Persistent state changes and verification evidence",
    no_events: "Mission events will appear here.",
    tools_heading: "Bounded tool registry",
    tools_description: "Deterministic engineering services remain authoritative; the optional local model selects only among valid plans.",
    loading_tools: "Loading registered tools...",
    deterministic: "Deterministic",
    optional_model: "Optional model-assisted",
    no_tools: "No agent tools are registered.",
    approval_required: "Approval required",
    critical_excluded: "Critical loads excluded",
    model_calls: "{count} model calls",
    mission_state: "Mission state",
    waiting_decision: "Waiting for an operator decision",
    state_machine: "Persistent state machine",
    forecast_peak: "Forecast peak",
    response_required: "{value} kVA response required",
    configured_limit: "Configured limit",
    planning_reserve: "{value} kVA planning reserve",
    verified_result: "Verified result",
    pending: "Pending",
    headroom: "{value} kVA headroom",
    measured_after: "Measured after emulated execution",
    replans: "Replans",
    injected: "{name} injected",
    no_complication: "No complication injected yet",
    safety: "Safety",
    protected: "Protected",
    review: "Review",
    critical_actions: "{count} critical-load actions · live control off",
    approve_limits: "Approve with limits",
    modify_reserve: "Modify reserve",
    reject: "Reject",
    target_verified: "TARGET VERIFIED",
    target_not_met: "TARGET NOT MET",
    realised_headroom: "{realised} kVA realised · {headroom} kVA headroom",
    observation_complete: "Observation complete",
    default_rationale: "Deterministic engineering logic generated and ranked the candidate plans.",
    expected_response: "Expected response",
    plan_score: "Plan score",
    confidence: "Confidence",
    actions: "Actions",
    flexible_load: "Flexible load",
    no_actions: "No plan actions are available.",
    ready_facilities: "{status} · {count} facilities · live control off",
    busy_prepare: "Observing facilities and ranking safe plans...",
    busy_run: "Running observe → plan → approve → emulate → verify...",
    busy_modify: "Rebuilding the mission inside the modified constraint...",
    busy_approve: "Applying approval through the safety firewall...",
    toast_prepared: "Mission prepared. Review the plan and choose an approval decision.",
    toast_completed: "Resilient software-in-the-loop mission completed.",
    toast_modified: "Mission updated. The revised plan requires approval.",
    toast_decision: "Mission decision recorded: {decision}.",
    demo_failed: "Agent demo failed: {message}",
    preparation_failed: "Mission preparation failed: {message}",
    refresh_failed: "Agent refresh failed: {message}",
    runtime_failed: "Agent runtime failed to load: {message}",
    plan_suffix: "{strategy} plan"
  };

  const catalogs = {
    en,
    sn: {
      language_label: "Mutauro",
      hero_eyebrow: "SIMBA MUMIRIRIRI ANOZVITONGA WEKUSHANDISA MAGETSI",
      hero_title: "Isa chinangwa chemagetsi. Ongorora hurongwa. Siya mushandisi aine masimba.",
      hero_description: "Mumiririri anoongorora zvivako zvakagadzirirwa, anofembera kudiwa kwemagetsi, anoronga zviito zvakachengeteka zvisingabati mitoro yakakosha, anokumbira mvumo, anoita chete muchirimwa chekuedzesera, ozoongorora mhedzisiro uye orongazve pazvinenge zvichidiwa.",
      runtime_checking: "Kutarisa mashandiro emumiririri",
      software_only: "Kuedzesera musoftware chete",
      live_disabled: "Kudzima kana kubatidza magetsi chaiwo kwakavharwa.",
      firewall: "DZIVIRIRO YEMAGETSI INOSHANDA NEMITEMO YAKAJeka",
      firewall_description: "Mitoro yakakosha, mirairo yakasakara nemidziyo isingawanikwi zvinovharwa kusati kwaitwa chiito.",
      boundary_default: "Mvumo inodiwa. Kurongazve kunoramba kuri mukati memiganhu yakabvumirwa.",
      process_heading: "Zvinoitwa nemumiririri",
      process_description: "Maitiro ane miganhu uye anotevereka anoshandura chinangwa chemagetsi kuita mhinduro yakasimbiswa musoftware.",
      observe: "Ongorora", observe_detail: "Verenga zvivako zvose zvakagadzirirwa uye mamiriro ekutsva kwedata.",
      forecast: "Fembera", forecast_detail: "Fembera kudiwa kwekambasi uye ona kana muganhu uchidarika.",
      plan_safely: "Ronga zvakachengeteka", plan_detail: "Ronga mitoro inochinjika mushure mekuongororwa kwekuchengeteka.",
      approve: "Bvumira", approve_detail: "Mushandisi anobvumira, anoshandura, anoramba kana kuisa miganhu.",
      emulate: "Edzesera", emulate_detail: "Ita zviito muchirimwa chesofutiwe chete.",
      verify_replan: "Simbisa uye rongazve", verify_detail: "Yera mhinduro uye chinja kana zvakaitika zvasiyana.",
      mission_heading: "Basa rekuderedza peak yekambasi",
      goal_default: "Chengeta kudiwa kwekambasi kuri pasi pemuganhu wakagadzirirwa pasina kubata mitoro yakakosha.",
      complication_label: "Muedzo wekusimba",
      device_unavailable: "Mudziyo hauwanikwi", underperforming_action: "Chiito hachideredzi sezvaitarisirwa",
      prepare_mission: "Gadzirira basa", run_demo: "Mhanyisa muedzo wekusimba", refresh: "Vandudza",
      empty_start: "Tanga basa kuti uongorore, uronge, ubvumire, uite uye usimbise.",
      approval_heading: "Basa nemvumo", approval_description: "Bvumira, shandura, ramba kana bvumira nemiganhu yakajeka",
      no_mission: "Hapana basa ragadzirirwa panguva ino.", events_heading: "Nhoroondo yezviitiko", events_description: "Shanduko dzemamiriro nehumbowo hwekusimbisa", no_events: "Zviitiko zvebasa zvichaonekwa pano.",
      tools_heading: "Zvishandiso zvine miganhu", tools_description: "Masevhisi einjiniya ane mitemo ndiwo ane masimba; modhi yemuno inosarudza chete pakati pehurongwa hwakabvumirwa.", loading_tools: "Kurodha zvishandiso...",
      deterministic: "Zvinotongwa nemitemo", optional_model: "Modhi inoshandiswa kana ichidiwa", no_tools: "Hapana zvishandiso zvemumiririri zvakanyoreswa.",
      approval_required: "Mvumo inodiwa", critical_excluded: "Mitoro yakakosha yabviswa", model_calls: "Kudanwa kwemodhi: {count}",
      mission_state: "Mamiriro ebasa", waiting_decision: "Kumirira chisarudzo chemushandisi", state_machine: "Mamiriro anochengetwa",
      forecast_peak: "Peak yakafemberwa", response_required: "Kuderedzwa kwe{value} kVA kunodiwa", configured_limit: "Muganhu wakagadzirirwa", planning_reserve: "Reserve yekuronga {value} kVA",
      verified_result: "Mhedzisiro yakasimbiswa", pending: "Zvakamirira", headroom: "Headroom {value} kVA", measured_after: "Zvinoyerwa mushure mekuedzesera",
      replans: "Kurongazve", injected: "{name} yaiswa", no_complication: "Hapana dambudziko raiswa parizvino", safety: "Kuchengeteka", protected: "Yakachengetedzwa", review: "Ongorora", critical_actions: "Zviito pamitoro yakakosha: {count} · live control yakavharwa",
      approve_limits: "Bvumira nemiganhu", modify_reserve: "Shandura reserve", reject: "Ramba", target_verified: "CHINANGWA CHASIMBISWA", target_not_met: "CHINANGWA HACHISATI CHASVIKWA", realised_headroom: "{realised} kVA yaderedzwa · {headroom} kVA yasara",
      observation_complete: "Kuongorora kwapera", default_rationale: "Mitemo yeinjiniya yakagadzira uye yakaronga hurongwa hunobvira.", expected_response: "Mhinduro inotarisirwa", plan_score: "Chiyero chehurongwa", confidence: "Kuvimbika", actions: "Zviito", flexible_load: "Mutoro unochinjika", no_actions: "Hapana zviito zvehurongwa zviripo.", ready_facilities: "{status} · zvivako {count} · live control yakavharwa",
      busy_prepare: "Kuongorora zvivako uye kuronga hurongwa hwakachengeteka...", busy_run: "Kuongorora → kuronga → kubvumira → kuedzesera → kusimbisa...", busy_modify: "Kuvakazve basa mukati memuganhu mutsva...", busy_approve: "Kushandisa mvumo kuburikidza nedziviriro yekuchengeteka...",
      toast_prepared: "Basa ragadzirwa. Ongorora hurongwa wosarudza mvumo.", toast_completed: "Basa rekuedzesera rakapedzwa.", toast_modified: "Basa rashandurwa. Hurongwa hutsva hunoda mvumo.", toast_decision: "Chisarudzo chebasa chachengetwa: {decision}.", plan_suffix: "Hurongwa hwe{strategy}"
    },
    nd: {
      language_label: "Ulimi",
      hero_eyebrow: "I-SIMBA EJENTI EZIMELEYO YOKUPHATHA AMANDLA",
      hero_title: "Misa umgomo wamandla. Hlola icebo. Umqhubi ahlale elawula.",
      hero_description: "I-ejenti ibona izakhiwo ezihleliwe, ibikezela ukusetshenziswa kwamandla, ikhethe izenzo eziphephileyo ezingathinti imithwalo eqakathekileyo, icele imvumo, isebenze kuphela emshinini wokulingisa, iqinisekise impumela njalo ihlele kutsha nxa kudingeka.",
      runtime_checking: "Ukuhlola ukusebenza kwe-ejenti", software_only: "Ukulingisa nge-software kuphela", live_disabled: "Ukutshintsha ugetsi lwangempela kuvaliwe.",
      firewall: "UMGOQO WOKUPHEPHA KWAMANDLA OSEBENZA NGEMITHETHO", firewall_description: "Imithwalo eqakathekileyo, imilayo ephelelwe yisikhathi lamadivayisi angatholakaliyo kuyavinjwa kungakenziwa.", boundary_default: "Imvumo iyadingeka. Ukuhlela kutsha kuhlala phakathi kwemingcele evunyelweyo.",
      process_heading: "Okwenziwa yi-ejenti", process_description: "Uhlelo olulinganiselweyo njalo olulandelekayo luguqula umgomo wamandla ube yimpendulo eqinisekisiweyo ye-software.",
      observe: "Bona", observe_detail: "Funda zonke izakhiwo ezihleliwe lokuthi idatha isentsha yini.", forecast: "Bikezela", forecast_detail: "Bikezela ukusetshenziswa kwekhempasi ubone ukweqa umngcele.", plan_safely: "Hlela ngokuphepha", plan_detail: "Linganisa imithwalo eguqukayo ngemva kokuhlolwa kokuphepha.", approve: "Vumela", approve_detail: "Umqhubi angavumela, alungise, ale kumbe abeke imingcele.", emulate: "Lingisa", emulate_detail: "Yenza izenzo emshinini we-software kuphela.", verify_replan: "Qinisekisa uhlele kutsha", verify_detail: "Linganisa impumela uguqule nxa kwehluka kulokho obekulindelwe.",
      mission_heading: "Umsebenzi wokwehlisa i-peak yekhempasi", goal_default: "Gcina ukusetshenziswa kwekhempasi kungaphansi komngcele ngaphandle kokuthinta imithwalo eqakathekileyo.", complication_label: "Ukuhlolwa kokuqina", device_unavailable: "Idivayisi ayitholakali", underperforming_action: "Isenzo asisebenzi njengokulindelweyo", prepare_mission: "Lungisa umsebenzi", run_demo: "Qalisa ukuhlolwa kokuqina", refresh: "Vuselela",
      empty_start: "Qalisa umsebenzi ukuze ubone, uhlele, uvumele, wenze njalo uqinisekise.", approval_heading: "Umsebenzi lemvumo", approval_description: "Vumela, lungisa, ala kumbe vumela ngemingcele ecacileyo", no_mission: "Akukho msebenzi olungisiweyo khathesi.", events_heading: "Umlando wezenzakalo", events_description: "Ukutshintsha kwezimo lobufakazi bokuqinisekisa", no_events: "Izenzakalo zomsebenzi zizabonakala lapha.", tools_heading: "Amathuluzi alinganiselweyo", tools_description: "Imithetho yobunjiniyela yiyo elawulayo; imodeli yendawo ikhetha kuphela phakathi kwamacebo avunyelweyo.", loading_tools: "Kulayishwa amathuluzi...", deterministic: "Kulawulwa yimithetho", optional_model: "Imodeli esetshenziswa nxa idingeka", no_tools: "Akukho mathuluzi e-ejenti abhalisiweyo.",
      approval_required: "Imvumo iyadingeka", critical_excluded: "Imithwalo eqakathekileyo isusiwe", model_calls: "Ukubizwa kwemodeli: {count}", mission_state: "Isimo somsebenzi", waiting_decision: "Kulindwe isinqumo somqhubi", state_machine: "Isimo esigcinwayo", forecast_peak: "I-peak ebikezelweyo", response_required: "Kudingeka ukwehliswa kwe{value} kVA", configured_limit: "Umngcele ohleliweyo", planning_reserve: "I-reserve yokuhlela {value} kVA", verified_result: "Impumela eqinisekisiweyo", pending: "Kusalindwe", headroom: "I-headroom {value} kVA", measured_after: "Kulinganiswa ngemva kokulingisa", replans: "Ukuhlela kutsha", injected: "{name} kufakiwe", no_complication: "Akukho uhlupho olufakiweyo khathesi", safety: "Ukuphepha", protected: "Kuvikelekile", review: "Hlola", critical_actions: "Izenzo emithwalweni eqakathekileyo: {count} · live control ivaliwe", approve_limits: "Vumela ngemingcele", modify_reserve: "Lungisa i-reserve", reject: "Ala", target_verified: "UMGOMO UQINISEKISIWE", target_not_met: "UMGOMO AWUKAFIKELELWA", realised_headroom: "{realised} kVA yehlisiwe · {headroom} kVA isele", observation_complete: "Ukubona kuphelile", default_rationale: "Imithetho yobunjiniyela yakha yalinganisa amacebo avumelekileyo.", expected_response: "Impendulo elindelweyo", plan_score: "Isilinganiso secebo", confidence: "Ukuqiniseka", actions: "Izenzo", flexible_load: "Umthwalo oguqukayo", no_actions: "Akukho zenzo zecebo ezikhona.", ready_facilities: "{status} · izakhiwo {count} · live control ivaliwe", busy_prepare: "Ukuhlola izakhiwo lokulinganisa amacebo aphephileyo...", busy_run: "Ukubona → ukuhlela → ukuvumela → ukulingisa → ukuqinisekisa...", busy_modify: "Kwakhiwa umsebenzi kutsha phakathi komngcele omtsha...", busy_approve: "Kusetshenziswa imvumo ngomgoqo wokuphepha...", toast_prepared: "Umsebenzi usulungisiwe. Hlola icebo ukhethe imvumo.", toast_completed: "Umsebenzi wokulingisa usuqediwe.", toast_modified: "Umsebenzi usulungisiwe. Icebo elitsha lifuna imvumo.", toast_decision: "Isinqumo somsebenzi sigciniwe: {decision}.", plan_suffix: "Icebo le-{strategy}"
    },
    sw: {
      language_label: "Lugha", hero_eyebrow: "WAKALA HURU WA UENDESHAJI WA NISHATI WA SIMBA", hero_title: "Weka lengo la nishati. Kagua mpango. Mwendeshaji aendelee kudhibiti.", hero_description: "Wakala hutazama vituo vilivyosanidiwa, hutabiri mahitaji, hupanga hatua salama zisizo za mizigo muhimu, huomba idhini, hutekeleza kwenye mtambo wa programu pekee, huthibitisha matokeo na kupanga upya inapohitajika.", runtime_checking: "Inakagua mazingira ya wakala", software_only: "Majaribio ya programu pekee", live_disabled: "Udhibiti wa moja kwa moja wa umeme umezimwa.", firewall: "KINGA THABITI YA USALAMA WA NISHATI", firewall_description: "Mizigo muhimu, amri zilizopitwa na muda na vifaa visivyopatikana huzuiwa kabla ya utekelezaji.", boundary_default: "Idhini inahitajika. Upangaji upya hubaki ndani ya mipaka iliyoidhinishwa.", process_heading: "Kile wakala anachofanya", process_description: "Mzunguko wenye mipaka na unaokaguliwa hubadilisha lengo la nishati kuwa hatua ya programu iliyothibitishwa.", observe: "Tazama", observe_detail: "Soma kila kituo na hali ya uhalali wa data.", forecast: "Tabiri", forecast_detail: "Tabiri mahitaji ya kampasi na gundua kuvuka kikomo.", plan_safely: "Panga kwa usalama", plan_detail: "Panga mizigo inayoweza kubadilika baada ya ukaguzi wa usalama.", approve: "Idhinisha", approve_detail: "Mwendeshaji aidhinishe, abadili, akatae au aweke mipaka.", emulate: "Iga", emulate_detail: "Tekeleza hatua kwenye mtambo wa programu pekee.", verify_replan: "Thibitisha na panga upya", verify_detail: "Pima matokeo na ubadilike hali halisi ikitofautiana.", mission_heading: "Jukumu la kilele cha kampasi", goal_default: "Weka mahitaji ya kampasi chini ya kikomo bila kugusa mizigo muhimu.", complication_label: "Jaribio la ustahimilivu", device_unavailable: "Kifaa hakipatikani", underperforming_action: "Hatua haifikii matarajio", prepare_mission: "Andaa jukumu", run_demo: "Endesha jaribio la ustahimilivu", refresh: "Onyesha upya", empty_start: "Anzisha jukumu ili kutazama, kupanga, kuidhinisha, kutekeleza na kuthibitisha.", approval_heading: "Jukumu na idhini", approval_description: "Idhinisha, badili, kataa au idhinisha kwa mipaka wazi", no_mission: "Hakuna jukumu lililoandaliwa.", events_heading: "Mfuatano wa matukio", events_description: "Mabadiliko ya hali na ushahidi wa uthibitishaji", no_events: "Matukio ya jukumu yataonekana hapa.", tools_heading: "Sajili ya zana zenye mipaka", tools_description: "Huduma za uhandisi ndizo zenye mamlaka; modeli ya ndani huchagua tu mipango halali.", loading_tools: "Inapakia zana...", deterministic: "Ya kanuni", optional_model: "Husaidiwa na modeli inapohitajika", no_tools: "Hakuna zana za wakala zilizosajiliwa.", approval_required: "Idhini inahitajika", critical_excluded: "Mizigo muhimu imeondolewa", model_calls: "Miito ya modeli: {count}", mission_state: "Hali ya jukumu", waiting_decision: "Inasubiri uamuzi wa mwendeshaji", state_machine: "Hali inayohifadhiwa", forecast_peak: "Kilele kilichotabiriwa", response_required: "Upunguzaji wa {value} kVA unahitajika", configured_limit: "Kikomo kilichowekwa", planning_reserve: "Akiba ya mpango {value} kVA", verified_result: "Matokeo yaliyothibitishwa", pending: "Inasubiri", headroom: "Nafasi {value} kVA", measured_after: "Hupimwa baada ya utekelezaji wa kuiga", replans: "Mipango mipya", injected: "{name} imeingizwa", no_complication: "Hakuna tatizo lililoingizwa bado", safety: "Usalama", protected: "Imelindwa", review: "Kagua", critical_actions: "Hatua za mizigo muhimu: {count} · udhibiti wa moja kwa moja umezimwa", approve_limits: "Idhinisha kwa mipaka", modify_reserve: "Badili akiba", reject: "Kataa", target_verified: "LENGO LIMETHIBITISHWA", target_not_met: "LENGO HALIJAFIKIWA", realised_headroom: "{realised} kVA imepunguzwa · nafasi {headroom} kVA", observation_complete: "Uchunguzi umekamilika", default_rationale: "Kanuni za uhandisi ziliunda na kupanga mipango halali.", expected_response: "Matokeo yanayotarajiwa", plan_score: "Alama ya mpango", confidence: "Uhakika", actions: "Hatua", flexible_load: "Mzigo unaobadilika", no_actions: "Hakuna hatua za mpango.", ready_facilities: "{status} · vituo {count} · udhibiti wa moja kwa moja umezimwa", busy_prepare: "Inatazama vituo na kupanga mipango salama...", busy_run: "Kutazama → kupanga → kuidhinisha → kuiga → kuthibitisha...", busy_modify: "Inaunda jukumu upya ndani ya sharti jipya...", busy_approve: "Inatumia idhini kupitia kinga ya usalama...", toast_prepared: "Jukumu limeandaliwa. Kagua mpango na uchague uamuzi.", toast_completed: "Jukumu la majaribio limekamilika.", toast_modified: "Jukumu limebadilishwa. Mpango mpya unahitaji idhini.", toast_decision: "Uamuzi wa jukumu umehifadhiwa: {decision}.", plan_suffix: "Mpango wa {strategy}"
    },
    zu: {
      language_label: "Ulimi", hero_eyebrow: "I-SIMBA UMMELI OZIPHATHELAYO WOKUSEBENZA KWAMANDLA", hero_title: "Setha inhloso yamandla. Hlola uhlelo. Umsebenzisi ahlale elawula.", hero_description: "Ummeli ubheka izikhungo ezilungisiwe, ubikezela isidingo, uhlele izenzo eziphephile ezingathinti imithwalo ebalulekile, ucele imvume, usebenze kuphela embonini yesofthiwe, uqinisekise umphumela futhi uhlele kabusha uma kudingeka.", runtime_checking: "Ihlola ukusebenza kommeli", software_only: "Ukulingisa ngesofthiwe kuphela", live_disabled: "Ukulawula ugesi wangempela kukhutshaziwe.", firewall: "ISIVIMBELO ESINQUNYIWE SOKUPHEPHA KWAMANDLA", firewall_description: "Imithwalo ebalulekile, imiyalo ephelelwe isikhathi namadivayisi angatholakali kuvinjelwa ngaphambi kokusebenza.", boundary_default: "Imvume iyadingeka. Ukuhlela kabusha kuhlala ngaphakathi kwemikhawulo evunyelwe.", process_heading: "Okwenziwa ummeli", process_description: "Umjikelezo onemingcele futhi olandelekayo uguqula inhloso yamandla ibe yimpendulo yesofthiwe eqinisekisiwe.", observe: "Bheka", observe_detail: "Funda zonke izikhungo ezilungisiwe nobusha bedatha.", forecast: "Bikezela", forecast_detail: "Bikezela isidingo sekhampasi futhi uthole ukweqa umkhawulo.", plan_safely: "Hlela ngokuphepha", plan_detail: "Linganisa imithwalo eguquguqukayo ngemva kokuhlolwa kokuphepha.", approve: "Vumela", approve_detail: "Umsebenzisi avumele, ashintshe, anqabe noma abeke imikhawulo.", emulate: "Lingisa", emulate_detail: "Sebenzisa izenzo embonini yesofthiwe kuphela.", verify_replan: "Qinisekisa bese uhlela kabusha", verify_detail: "Linganisa impendulo bese uzivumelanisa uma iqiniso lehluka.", mission_heading: "Umsebenzi wokunciphisa ukuphakama kwekhampasi", goal_default: "Gcina isidingo sekhampasi ngaphansi komkhawulo ngaphandle kokuthinta imithwalo ebalulekile.", complication_label: "Ukuhlolwa kokuqina", device_unavailable: "Idivayisi ayitholakali", underperforming_action: "Isenzo asenzi njengokulindelekile", prepare_mission: "Lungiselela umsebenzi", run_demo: "Qalisa ukuhlolwa kokuqina", refresh: "Vuselela", empty_start: "Qala umsebenzi ukuze ubheke, uhlele, uvumele, wenze futhi uqinisekise.", approval_heading: "Umsebenzi nemvume", approval_description: "Vumela, shintsha, nqaba noma uvumele ngemikhawulo ecacile", no_mission: "Awukho umsebenzi olungisiwe okwamanje.", events_heading: "Umlando wezenzakalo", events_description: "Ukushintsha kwezimo nobufakazi bokuqinisekisa", no_events: "Izenzakalo zomsebenzi zizovela lapha.", tools_heading: "Uhlu lwamathuluzi anemingcele", tools_description: "Izinsizakalo zobunjiniyela zihlala zinamandla; imodeli yendawo ikhetha kuphela ezinhlelweni ezivumelekile.", loading_tools: "Ilayisha amathuluzi...", deterministic: "Kunqunywa yimithetho", optional_model: "Imodeli isiza uma idingeka", no_tools: "Awekho amathuluzi ommeli abhalisiwe.", approval_required: "Imvume iyadingeka", critical_excluded: "Imithwalo ebalulekile ikhishiwe", model_calls: "Izingcingo zemodeli: {count}", mission_state: "Isimo somsebenzi", waiting_decision: "Kulindwe isinqumo somsebenzisi", state_machine: "Isimo esigcinwayo", forecast_peak: "Ukuphakama okubikezelwe", response_required: "Kudingeka ukuncipha kwe-{value} kVA", configured_limit: "Umkhawulo olungisiwe", planning_reserve: "Isigcini sokuhlela {value} kVA", verified_result: "Umphumela oqinisekisiwe", pending: "Kusalindwe", headroom: "Isikhala {value} kVA", measured_after: "Kulinganiswa ngemva kokulingisa", replans: "Ukuhlela kabusha", injected: "{name} kufakiwe", no_complication: "Akukho nkinga efakiwe okwamanje", safety: "Ukuphepha", protected: "Kuvikelekile", review: "Hlola", critical_actions: "Izenzo emithwalweni ebalulekile: {count} · ukulawula kwangempela kuvaliwe", approve_limits: "Vumela ngemikhawulo", modify_reserve: "Shintsha isigcini", reject: "Nqaba", target_verified: "INHLOSO IQINISEKISIWE", target_not_met: "INHLOSO AYIKAFINYELELWA", realised_headroom: "{realised} kVA yehlisiwe · isikhala {headroom} kVA", observation_complete: "Ukubheka kuqediwe", default_rationale: "Imithetho yobunjiniyela yakha futhi yalinganisa izinhlelo ezivumelekile.", expected_response: "Impendulo elindelekile", plan_score: "Isilinganiso sohlelo", confidence: "Ukuqiniseka", actions: "Izenzo", flexible_load: "Umthwalo oguquguqukayo", no_actions: "Azikho izenzo zohlelo.", ready_facilities: "{status} · izikhungo {count} · ukulawula kwangempela kuvaliwe", busy_prepare: "Ihlola izikhungo futhi ilinganisa izinhlelo eziphephile...", busy_run: "Ukubheka → ukuhlela → ukuvumela → ukulingisa → ukuqinisekisa...", busy_modify: "Yakha umsebenzi kabusha ngaphakathi komkhawulo omusha...", busy_approve: "Isebenzisa imvume ngesivimbelo sokuphepha...", toast_prepared: "Umsebenzi usulungisiwe. Hlola uhlelo bese ukhetha isinqumo.", toast_completed: "Umsebenzi wokulingisa usuqediwe.", toast_modified: "Umsebenzi ushintshiwe. Uhlelo olusha ludinga imvume.", toast_decision: "Isinqumo somsebenzi sigciniwe: {decision}.", plan_suffix: "Uhlelo lwe-{strategy}"
    }
  };

  const labelCatalogs = {
    sn: {TARGET_MET: "Chinangwa Chasvikwa", AWAITING_APPROVAL: "Kumirira Mvumo", APPROVED: "Zvatenderwa", EXECUTING: "Kuita", OBSERVING_RESPONSE: "Kuongorora Mhinduro", REPLANNING: "Kurongazve", PLAN_READY: "Hurongwa Hwagadzirira", PLANNING: "Kuronga", RISK_DETECTED: "Njodzi Yaonekwa", FAILED: "Zvaramba", REJECTED: "Zvarambwa", mission_target_met: "Chinangwa Chebasa Chasvikwa", impact_verified: "Mhedzisiro Yasimbiswa", replanning_started: "Kurongazve Kwatanga", replan_ready: "Hurongwa Hutsva Hwagadzirira", complication_injected: "Dambudziko Raiswa", action_blocked_by_safety_firewall: "Chiito Chavharwa Nedziviriro", emulated_action_executed: "Chiito Chekuedzesera Chaitwa", mission_approved: "Basa Ratenderwa", plan_execution_started: "Kuita Hurongwa Kwatanga", device_unavailable: "Mudziyo Hauwanikwi", underperforming_action: "Chiito Chaderera"},
    nd: {TARGET_MET: "Umgomo Ufinyelelwe", AWAITING_APPROVAL: "Kulindwe Imvumo", APPROVED: "Kuvunyelwe", EXECUTING: "Kuyasebenza", OBSERVING_RESPONSE: "Kuhlolwa Impendulo", REPLANNING: "Kuhlelwa Kutsha", PLAN_READY: "Icebo Selilungile", PLANNING: "Kuyahlelwa", RISK_DETECTED: "Ingozi Ibonakele", FAILED: "Kwehlulekile", REJECTED: "Kwaliwe", mission_target_met: "Umgomo Womsebenzi Ufinyelelwe", impact_verified: "Impumela Iqinisekisiwe", replanning_started: "Ukuhlela Kutsha Kuqalile", replan_ready: "Icebo Elitsha Selilungile", complication_injected: "Uhlupho Lufakiwe", action_blocked_by_safety_firewall: "Isenzo Sivinjwe Ngokuphepha", emulated_action_executed: "Isenzo Sokulingisa Senziwe", mission_approved: "Umsebenzi Uvunyelwe", plan_execution_started: "Ukuqalisa Icebo", device_unavailable: "Idivayisi Ayitholakali", underperforming_action: "Isenzo Asisebenzi Kahle"},
    sw: {TARGET_MET: "Lengo Limefikiwa", AWAITING_APPROVAL: "Inasubiri Idhini", APPROVED: "Imeidhinishwa", EXECUTING: "Inatekeleza", OBSERVING_RESPONSE: "Inakagua Matokeo", REPLANNING: "Inapanga Upya", PLAN_READY: "Mpango Uko Tayari", PLANNING: "Inapanga", RISK_DETECTED: "Hatari Imegunduliwa", FAILED: "Imeshindwa", REJECTED: "Imekataliwa", mission_target_met: "Lengo la Jukumu Limefikiwa", impact_verified: "Matokeo Yamethibitishwa", replanning_started: "Upangaji Upya Umeanza", replan_ready: "Mpango Mpya Uko Tayari", complication_injected: "Tatizo Limeingizwa", action_blocked_by_safety_firewall: "Hatua Imezuiwa na Usalama", emulated_action_executed: "Hatua ya Kuiga Imetekelezwa", mission_approved: "Jukumu Limeidhinishwa", plan_execution_started: "Utekelezaji wa Mpango Umeanza", device_unavailable: "Kifaa Hakipatikani", underperforming_action: "Hatua Haifikii Matarajio"},
    zu: {TARGET_MET: "Inhloso Ifinyelelwe", AWAITING_APPROVAL: "Kulindwe Imvume", APPROVED: "Kuvunyelwe", EXECUTING: "Kuyasebenza", OBSERVING_RESPONSE: "Kuhlolwa Impendulo", REPLANNING: "Kuhlelwa Kabusha", PLAN_READY: "Uhlelo Selulungile", PLANNING: "Kuyahlelwa", RISK_DETECTED: "Ingozi Itholakele", FAILED: "Kwehlulekile", REJECTED: "Kwenqatshiwe", mission_target_met: "Inhloso Yomsebenzi Ifinyelelwe", impact_verified: "Umphumela Uqinisekisiwe", replanning_started: "Ukuhlela Kabusha Kuqalile", replan_ready: "Uhlelo Olusha Selulungile", complication_injected: "Inkinga Ifakiwe", action_blocked_by_safety_firewall: "Isenzo Sivinjwe Ukuphepha", emulated_action_executed: "Isenzo Sokulingisa Senziwe", mission_approved: "Umsebenzi Uvunyelwe", plan_execution_started: "Ukuqalisa Uhlelo", device_unavailable: "Idivayisi Ayitholakali", underperforming_action: "Isenzo Asenzi Kahle"}
  };

  let current = localStorage.getItem("simba-agent-language") || "en";
  if (!catalogs[current]) current = "en";

  function format(template, values) {
    return String(template).replace(/\{([a-z_]+)\}/gi, (_, key) => values?.[key] ?? "");
  }

  function t(key, values = {}) {
    return format(catalogs[current]?.[key] ?? en[key] ?? key, values);
  }

  function label(value) {
    const source = String(value || "");
    const translated = labelCatalogs[current]?.[source];
    if (translated) return translated;
    return source.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, character => character.toUpperCase());
  }

  function applyStatic(root = document) {
    root.querySelectorAll("[data-i18n]").forEach(node => {
      node.textContent = t(node.dataset.i18n);
    });
    document.documentElement.lang = current;
  }

  function setLanguage(code) {
    current = catalogs[code] ? code : "en";
    localStorage.setItem("simba-agent-language", current);
    applyStatic(document);
    window.dispatchEvent(new CustomEvent("simba-language-changed", {detail: {language: current}}));
  }

  window.SimbaI18n = {languages, t, label, applyStatic, setLanguage, language: () => current};
})();
