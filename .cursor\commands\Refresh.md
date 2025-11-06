//Refresh.md

{
  "name": "Refresh Persona",
  "command": "/refresh",
  "actions": [
    {
      "type": "read_file",
      "path": "C:/Users/AM - Shift/Documents/Scripts For Modifying/Projects/ScriptsForWork/GA4 Script Tools/refresh-persona.md"
    },
    {
      "type": "set_system_prompt",
      "content": "{{file_contents}}"
    }
  ]
}
