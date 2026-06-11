
/**
 * Quant Nanggroe AI v11.1 - AutoSwitch API System (Diamond Glass Edition)
 * Handles automatic failover, retries, and proactive health monitoring.
 */

export interface AutoSwitchProvider<T, R> {
    name: string;
    id: string;
    execute: (params: T) => Promise<R>;
    isAvailable?: () => boolean;
}

export interface AutoSwitchOptions {
    maxRetries?: number;
    retryDelay?: number;
    enableAutoSwitch?: boolean;
    onProviderChange?: (oldProvider: string, newProvider: string) => void;
}

export interface HealthStatus {
    lastSuccess: number;
    lastFailure: number;
    failureCount: number;
    successCount: number;
}

export class AutoSwitch<T, R> {
    private static globalHealth: Record<string, HealthStatus> = {};
    private providers: AutoSwitchProvider<T, R>[];
    private options: AutoSwitchOptions;
    private cooldowns: Record<string, number> = {};

    constructor(providers: AutoSwitchProvider<T, R>[], options: AutoSwitchOptions = {}) {
        this.providers = providers;
        this.options = {
            maxRetries: 3,
            retryDelay: 2000,
            enableAutoSwitch: true,
            ...options
        };
    }

    private updateHealth(id: string, success: boolean) {
        if (!AutoSwitch.globalHealth[id]) {
            AutoSwitch.globalHealth[id] = { lastSuccess: 0, lastFailure: 0, failureCount: 0, successCount: 0 };
        }
        const health = AutoSwitch.globalHealth[id];
        if (success) {
            health.lastSuccess = Date.now();
            health.successCount++;
            health.failureCount = Math.max(0, health.failureCount - 1); // Decay failure count
        } else {
            health.lastFailure = Date.now();
            health.failureCount++;
        }
    }

    public static getHealthReport() {
        return AutoSwitch.globalHealth;
    }

    private sleep(ms: number) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    private isCoolingDown(id: string): boolean {
        // Check local cooldown
        const cooldownUntil = this.cooldowns[id];
        if (cooldownUntil && Date.now() < cooldownUntil) return true;

        // Check global health-based cooldown (proactive)
        const health = AutoSwitch.globalHealth[id];
        if (health && health.failureCount > 5) {
            // If more than 5 failures, cool down for 5 minutes unless last success was very recent
            if (Date.now() - health.lastFailure < 300000 && Date.now() - health.lastSuccess > 60000) {
                return true;
            }
        }
        
        return false;
    }

    private setCooldown(id: string, ms: number = 60000) {
        this.cooldowns[id] = Date.now() + ms;
    }

    async execute(params: T): Promise<{ data: R; providerId: string }> {
        let lastError: Error | null = null;
        
        // Filter and sort providers by health
        const availableProviders = this.providers
            .filter(p => {
                if (p.isAvailable && !p.isAvailable()) return false;
                if (this.isCoolingDown(p.id)) return false;
                return true;
            })
            .sort((a, b) => {
                const healthA = AutoSwitch.globalHealth[a.id] || { failureCount: 0, successCount: 0 };
                const healthB = AutoSwitch.globalHealth[b.id] || { failureCount: 0, successCount: 0 };
                // Prefer lower failure count, then higher success count
                if (healthA.failureCount !== healthB.failureCount) return healthA.failureCount - healthB.failureCount;
                return healthB.successCount - healthA.successCount;
            });

        if (availableProviders.length === 0) {
            throw new Error("No available API providers found or all are in healthy cooldown.");
        }

        for (let i = 0; i < availableProviders.length; i++) {
            const provider = availableProviders[i];
            let retries = 0;

            while (retries < (this.options.maxRetries || 3)) {
                try {
                    console.log(`[AutoSwitch] Attempting with ${provider.name} (${provider.id})...`);
                    const data = await provider.execute(params);
                    this.updateHealth(provider.id, true);
                    return { data, providerId: provider.id };
                } catch (error: unknown) {
                    this.updateHealth(provider.id, false);
                    const err = error instanceof Error ? error : new Error(String(error));
                    const status = (err as { status?: number }).status || (err as { response?: { status?: number } }).response?.status;
                    const message = err.message || "";

                    // If rate limited, retry with exponential backoff
                    if (status === 429 || message.includes('429') || message.toLowerCase().includes('rate limit')) {
                        const delay = (this.options.retryDelay || 2000) * Math.pow(2, retries);
                        console.warn(`[AutoSwitch] ${provider.name} rate limited. Retrying in ${delay}ms...`);
                        await this.sleep(delay);
                        retries++;
                        continue;
                    }

                    // For other errors, log and try next provider if auto-switch is enabled
                    console.error(`[AutoSwitch] ${provider.name} failed:`, message);
                    this.setCooldown(provider.id, 30000); // 30s cooldown for non-rate-limit errors
                    lastError = err;
                    break; // Exit retry loop to try next provider
                }
            }

            if (!this.options.enableAutoSwitch) break;
            
            if (i < availableProviders.length - 1) {
                console.info(`[AutoSwitch] Switching from ${provider.name} to ${availableProviders[i+1].name}...`);
                if (this.options.onProviderChange) {
                    this.options.onProviderChange(provider.id, availableProviders[i+1].id);
                }
            }
        }

        throw lastError || new Error("All providers failed to execute.");
    }
}
