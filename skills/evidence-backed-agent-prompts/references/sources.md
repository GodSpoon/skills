# Sources and original reference case

## Workflow sources
Reviewed primary sources for the Hermes/OMP revision:
https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills
https://github.com/can1357/oh-my-pi/blob/main/docs/skills.md
https://github.com/can1357/oh-my-pi/blob/main/docs/cli-reference.md
https://github.com/can1357/oh-my-pi/blob/main/docs/rpc.md
https://github.com/can1357/oh-my-pi

Additional source locator for installation layout:
https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/skills-catalog.md

Maintain a task-specific ledger: ID | title | URL | version/scope | actual access date | claim supported | conflicts/limits | reviewed or supplied.

Local runtime evidence (omp v18.16.0 on Linux x64, 2026-11-13): `omp --help` flag list;
`~/.omp/agent/config.yml` model roles; `~/.omp/agent/models.db` catalog showing
`gemini-4-argon` / "Gemini 4 Argon" across the google, google-vertex, github-copilot,
venice, cloudflare-ai-gateway, commandcode, nanogpt, kilo and zenmux providers; a one-shot
smoke run returning `429 exceeded_current_quota_error` for the `kimi-code/kimi-for-coding`
role. Preserved in the public repo `evidence-backed-agent-prompts` under `integrations/omp/`.

## ESP32/Auvik original reference case
Preserved source locators from the earlier discussion; NOT all re-reviewed in this revision. Use only for relevant projects.

https://learn.lonelybinary.com/manuals/c3oled
https://learn.lonelybinary.com/boards/c3-oled
https://learn.lonelybinary.com/manuals/c3oled/arduino-ide-setup
https://learn.lonelybinary.com/manuals/c3oled/what-you-are-holding
https://lonelybinary.com/en-us/blogs/esp32-family-getting-started-guide/04_01_esp32_c3_oled
https://github.com/lonelybinary/ESP32
https://docs.platformio.org/en/latest/boards/espressif32/esp32-c3-devkitm-1.html
https://github.com/0neblock/Arduino_SNMP
https://github.com/0neblock/Arduino_SNMP/blob/master/examples/ESP32_SNMP/ESP32_SNMP.ino
https://docs.arduino.cc/libraries/snmp_agent/
https://docs.arduino.cc/libraries/libssh-esp32/
https://support.auvik.com/hc/en-us/articles/206617226-How-do-I-manage-custom-SNMP-Pollers
https://support.auvik.com/hc/en-us/articles/360000511366-SNMP-Poller-setting-alert-conditions
https://support.auvik.com/hc/en-us/articles/54058430994836-Alerting-on-SNMP-Pollers-and-Device-Tags-Current-Limitations-and-Workarounds
https://support.auvik.com/hc/en-us/articles/38583303072788-Troubleshooting-SNMP-from-the-Auvik-Collector
https://support.auvik.com/hc/en-us/articles/42342588622996-ACL-Requirements-for-Auvik-Integration
https://support.auvik.com/hc/en-us/articles/7792783916308-Alerts-FAQ
https://support.auvik.com/hc/en-us/articles/22685041592468-Auvik-Support-Limitations

Lessons from the user-reported successful run: SNMP primary/syslog supplementary; persistent leak latch distinct from current wet state; no invented fault supervision; OLED documentation conflict explicit; SSH maintenance distinct from native Auvik backup compatibility; authorized OID ownership; optional-feature isolation; honest test status.