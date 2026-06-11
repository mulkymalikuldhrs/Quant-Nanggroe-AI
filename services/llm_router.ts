
import { GoogleGenAI } from "@google/genai";
import { ApiKeys, LLMProvider, ModelOption } from "../types";
import { AutoSwitch, AutoSwitchProvider } from "./autoswitch";

// --- Provider Execution Helpers ---

async function callGoogle(apiKey: string, modelId: string, prompt: string, systemInstruction?: string) {
    const ai = new GoogleGenAI({ apiKey });
    
    const response = await ai.models.generateContent({
        model: modelId,
        contents: prompt,
        config: systemInstruction ? { systemInstruction } : undefined
    });
    return response.text || "No response text.";
}

async function callOpenAICompatible(baseUrl: string, apiKey: string, modelId: string, prompt: string, systemInstruction?: string) {
    const messages = [];
    if (systemInstruction) messages.push({ role: 'system', content: systemInstruction });
    messages.push({ role: 'user', content: prompt });

    const response = await fetch(`${baseUrl}/chat/completions`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify({
            model: modelId,
            messages: messages,
            temperature: 0.7
        })
    });

    if (!response.ok) {
        const err = await response.text();
        throw { status: response.status, message: err };
    }

    const data = await response.json();
    return data.choices?.[0]?.message?.content || "";
}

// --- The Router ---

export class LLMRouter {
    private keys: ApiKeys;
    private enableAutoSwitch: boolean;

    constructor(keys: ApiKeys, enableAutoSwitch: boolean) {
        this.keys = keys;
        this.enableAutoSwitch = enableAutoSwitch;
    }

    async generate(primaryModel: ModelOption, prompt: string, systemInstruction?: string): Promise<{ text: string, providerUsed: string }> {
        const providers: AutoSwitchProvider<{ prompt: string, systemInstruction?: string }, string>[] = [];

        // Primary Provider
        providers.push({
            name: primaryModel.name,
            id: primaryModel.provider,
            execute: (p) => this.executeCall(primaryModel, p.prompt, p.systemInstruction)
        });

        // Fallback Providers (only if auto-switch is enabled)
        if (this.enableAutoSwitch) {
            if (primaryModel.provider !== 'llm7') {
                providers.push({
                    name: 'LLM7 Core',
                    id: 'llm7',
                    execute: (p) => callOpenAICompatible('https://api.llm7.io/v1', this.keys.llm7 || 'unused', 'gpt-4.1-nano-2025-04-14', p.prompt, p.systemInstruction)
                });
            }

            if (primaryModel.provider !== 'groq' && this.keys.groq) {
                providers.push({
                    name: 'Llama 3 70B (Groq)',
                    id: 'groq',
                    execute: (p) => callOpenAICompatible('https://api.groq.com/openai/v1', this.keys.groq, 'llama3-70b-8192', p.prompt, p.systemInstruction)
                });
            }

            if (primaryModel.provider !== 'google' && this.keys.google) {
                providers.push({
                    name: 'Gemini Flash',
                    id: 'google',
                    execute: (p) => callGoogle(this.keys.google, 'gemini-3-flash-preview', p.prompt, p.systemInstruction)
                });
            }
        }

        const switcher = new AutoSwitch(providers, {
            enableAutoSwitch: this.enableAutoSwitch,
            maxRetries: 3
        });

        const result = await switcher.execute({ prompt, systemInstruction });
        return { text: result.data, providerUsed: result.providerId };
    }

    private async executeCall(model: ModelOption, prompt: string, systemInstruction?: string): Promise<string> {
        switch (model.provider) {
            case 'llm7':
                return callOpenAICompatible('https://api.llm7.io/v1', this.keys.llm7 || 'unused', model.id, prompt, systemInstruction);
            case 'google':
                return callGoogle(this.keys.google, model.id, prompt, systemInstruction);
            case 'groq':
                return callOpenAICompatible('https://api.groq.com/openai/v1', this.keys.groq, model.id, prompt, systemInstruction);
            case 'openai':
                return callOpenAICompatible('https://api.openai.com/v1', this.keys.openai, model.id, prompt, systemInstruction);
            default:
                throw new Error("Unknown provider: " + model.provider);
        }
    }
}
