using UnityEditor;
using UnityEngine;
using System;
using System.Collections.Generic;
using System.Text;
using System.Threading.Tasks;
using UnityEngine.Networking;

namespace AgentUnity.Editor
{
    /// <summary>
    /// Unity Editor window that provides a chat interface to the AgentUnity RunPod server.
    /// Communicates via the FastAPI REST endpoint on the pod.
    /// </summary>
    public class AgentUnityWindow : EditorWindow
    {
        // ── Settings ────────────────────────────────────────────────────
        private string _serverUrl = "http://localhost:8080"; // RunPod proxy URL or localhost
        private string _apiKey = "";
        private bool _showSettings = true;

        // ── Chat state ──────────────────────────────────────────────────
        private readonly List<ChatMessage> _messages = new();
        private string _inputText = "";
        private Vector2 _scrollPos;
        private bool _isWaiting;

        // ── Styles ──────────────────────────────────────────────────────
        private GUIStyle _userBubble;
        private GUIStyle _aiBubble;
        private GUIStyle _systemBubble;
        private GUIStyle _inputStyle;
        private bool _stylesInitialized;

        [MenuItem("AgentUnity/Chat Window")]
        public static void ShowWindow()
        {
            var window = GetWindow<AgentUnityWindow>("AgentUnity");
            window.minSize = new Vector2(400, 300);
        }

        private void OnEnable()
        {
            _serverUrl = EditorPrefs.GetString("AgentUnity_ServerUrl", "http://localhost:8080");
            _apiKey = EditorPrefs.GetString("AgentUnity_ApiKey", "");
        }

        private void InitStyles()
        {
            if (_stylesInitialized) return;

            _userBubble = new GUIStyle(EditorStyles.helpBox)
            {
                wordWrap = true,
                richText = true,
                padding = new RectOffset(10, 10, 8, 8),
                margin = new RectOffset(60, 10, 4, 4),
                fontSize = 12
            };

            _aiBubble = new GUIStyle(EditorStyles.helpBox)
            {
                wordWrap = true,
                richText = true,
                padding = new RectOffset(10, 10, 8, 8),
                margin = new RectOffset(10, 60, 4, 4),
                fontSize = 12
            };

            _systemBubble = new GUIStyle(EditorStyles.centeredGreyMiniLabel)
            {
                wordWrap = true,
                richText = true,
                padding = new RectOffset(10, 10, 4, 4),
                margin = new RectOffset(40, 40, 2, 2),
                fontSize = 10
            };

            _inputStyle = new GUIStyle(EditorStyles.textArea)
            {
                wordWrap = true,
                fontSize = 13,
                padding = new RectOffset(8, 8, 6, 6)
            };

            _stylesInitialized = true;
        }

        private void OnGUI()
        {
            InitStyles();

            // ── Settings panel ──────────────────────────────────────────
            _showSettings = EditorGUILayout.Foldout(_showSettings, "Connection Settings", true);
            if (_showSettings)
            {
                EditorGUI.indentLevel++;
                EditorGUI.BeginChangeCheck();

                _serverUrl = EditorGUILayout.TextField("Server URL", _serverUrl);
                _apiKey = EditorGUILayout.PasswordField("API Key", _apiKey);

                if (EditorGUI.EndChangeCheck())
                {
                    EditorPrefs.SetString("AgentUnity_ServerUrl", _serverUrl);
                    EditorPrefs.SetString("AgentUnity_ApiKey", _apiKey);
                }

                EditorGUILayout.BeginHorizontal();
                if (GUILayout.Button("Test Connection", GUILayout.Width(130)))
                    TestConnection();
                if (GUILayout.Button("Index Project (RAG)", GUILayout.Width(150)))
                    TriggerIndexing();
                if (GUILayout.Button("Clear Chat", GUILayout.Width(100)))
                    _messages.Clear();
                EditorGUILayout.EndHorizontal();

                EditorGUI.indentLevel--;
                EditorGUILayout.Space(4);
            }

            // ── Chat messages ───────────────────────────────────────────
            _scrollPos = EditorGUILayout.BeginScrollView(_scrollPos, GUILayout.ExpandHeight(true));

            if (_messages.Count == 0)
            {
                EditorGUILayout.LabelField("Send a message to start chatting with your AI agent.",
                    EditorStyles.centeredGreyMiniLabel);
            }

            foreach (var msg in _messages)
            {
                var style = msg.Role switch
                {
                    "user" => _userBubble,
                    "assistant" => _aiBubble,
                    _ => _systemBubble,
                };

                string prefix = msg.Role switch
                {
                    "user" => "<b>You:</b>\n",
                    "assistant" => $"<b>Agent</b> <color=#888>[{msg.Route}]</color>:\n",
                    _ => ""
                };

                EditorGUILayout.LabelField(prefix + msg.Content, style);
            }

            if (_isWaiting)
            {
                EditorGUILayout.LabelField("Agent is thinking...", _systemBubble);
            }

            EditorGUILayout.EndScrollView();

            // ── Input area ──────────────────────────────────────────────
            EditorGUILayout.BeginHorizontal();

            GUI.SetNextControlName("ChatInput");
            _inputText = EditorGUILayout.TextArea(_inputText, _inputStyle,
                GUILayout.MinHeight(40), GUILayout.MaxHeight(100));

            GUI.enabled = !_isWaiting && !string.IsNullOrWhiteSpace(_inputText);
            if (GUILayout.Button("Send", GUILayout.Width(60), GUILayout.Height(40)))
                SendMessage();
            GUI.enabled = true;

            EditorGUILayout.EndHorizontal();

            // Enter key to send
            if (Event.current.type == EventType.KeyDown && Event.current.keyCode == KeyCode.Return
                && !Event.current.shift && !_isWaiting && !string.IsNullOrWhiteSpace(_inputText))
            {
                SendMessage();
                Event.current.Use();
            }
        }

        // ── API calls ───────────────────────────────────────────────────

        private async void SendMessage()
        {
            if (string.IsNullOrWhiteSpace(_inputText) || _isWaiting) return;

            var userMsg = _inputText.Trim();
            _inputText = "";
            _messages.Add(new ChatMessage("user", userMsg));
            _isWaiting = true;
            Repaint();

            try
            {
                var json = BuildChatJson(userMsg);

                var url = $"{_serverUrl.TrimEnd('/')}/api/v1/agent/chat";
                var request = UnityWebRequest.Put(url, Encoding.UTF8.GetBytes(json));
                request.method = "POST";
                request.SetRequestHeader("Content-Type", "application/json");
                request.SetRequestHeader("X-API-Key", _apiKey);
                request.downloadHandler = new DownloadHandlerBuffer();
                request.timeout = 120;

                var op = request.SendWebRequest();

                while (!op.isDone)
                    await Task.Delay(100);

                if (request.result == UnityWebRequest.Result.Success)
                {
                    var response = JsonUtility.FromJson<ChatResponseJson>(request.downloadHandler.text);
                    _messages.Add(new ChatMessage("assistant", response.reply, response.route));
                }
                else
                {
                    _messages.Add(new ChatMessage("system",
                        $"Error: {request.error}\n{request.downloadHandler?.text}"));
                }

                request.Dispose();
            }
            catch (Exception ex)
            {
                _messages.Add(new ChatMessage("system", $"Exception: {ex.Message}"));
            }
            finally
            {
                _isWaiting = false;
                _scrollPos = new Vector2(0, float.MaxValue);
                Repaint();
            }
        }

        private async void TestConnection()
        {
            // Quick ping first
            var ping = UnityWebRequest.Get($"{_serverUrl}/api/v1/ping");
            ping.timeout = 5;
            var pingOp = ping.SendWebRequest();
            while (!pingOp.isDone) await Task.Delay(50);

            if (ping.result != UnityWebRequest.Result.Success)
            {
                _messages.Add(new ChatMessage("system", $"Connection failed: {ping.error}"));
                ping.Dispose();
                Repaint();
                return;
            }
            ping.Dispose();

            // Full health check
            var request = UnityWebRequest.Get($"{_serverUrl}/api/v1/health");
            request.timeout = 15;
            var op = request.SendWebRequest();
            while (!op.isDone) await Task.Delay(50);

            if (request.result == UnityWebRequest.Result.Success)
                _messages.Add(new ChatMessage("system", $"Connected!\n{request.downloadHandler.text}"));
            else
                _messages.Add(new ChatMessage("system", $"Server reachable but health check incomplete: {request.error}"));

            request.Dispose();
            Repaint();
        }

        private async void TriggerIndexing()
        {
            _messages.Add(new ChatMessage("system", "Indexing project via RAG pipeline..."));
            Repaint();

            var request = new UnityWebRequest($"{_serverUrl}/api/v1/rag/index", "POST");
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("X-API-Key", _apiKey);
            request.timeout = 300;
            var op = request.SendWebRequest();
            while (!op.isDone) await Task.Delay(100);

            if (request.result == UnityWebRequest.Result.Success)
                _messages.Add(new ChatMessage("system", $"✓ Indexing complete: {request.downloadHandler.text}"));
            else
                _messages.Add(new ChatMessage("system", $"✗ Indexing failed: {request.error}"));

            request.Dispose();
            Repaint();
        }

        // ── Helpers ─────────────────────────────────────────────────────

        private string BuildChatJson(string currentMessage)
        {
            var sb = new StringBuilder();
            sb.Append("{\"message\":\"");
            sb.Append(EscapeJson(currentMessage));
            sb.Append("\",\"history\":[");

            // Last 20 messages as history, excluding the current one just added
            int start = Math.Max(0, _messages.Count - 21);
            bool first = true;
            for (int i = start; i < _messages.Count - 1; i++)
            {
                var m = _messages[i];
                if (m.Role != "user" && m.Role != "assistant") continue;
                if (!first) sb.Append(",");
                first = false;
                sb.Append("{\"role\":\"");
                sb.Append(EscapeJson(m.Role));
                sb.Append("\",\"content\":\"");
                sb.Append(EscapeJson(m.Content));
                sb.Append("\"}");
            }

            sb.Append("]}");
            return sb.ToString();
        }

        private static string EscapeJson(string s)
        {
            return s.Replace("\\", "\\\\")
                    .Replace("\"", "\\\"")
                    .Replace("\n", "\\n")
                    .Replace("\r", "\\r")
                    .Replace("\t", "\\t");
        }

        // ── Data types ──────────────────────────────────────────────────

        private class ChatMessage
        {
            public string Role;
            public string Content;
            public string Route;

            public ChatMessage(string role, string content, string route = "")
            {
                Role = role;
                Content = content;
                Route = route;
            }
        }

        [Serializable]
        private class ChatResponseJson
        {
            public string reply;
            public string route;
            public int duration_ms;
        }
    }
}
