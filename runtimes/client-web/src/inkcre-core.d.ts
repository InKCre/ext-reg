declare module '@inkcre/core' {
  export interface ExtensionInstallInput {
    readonly name: string
    readonly version: string
    readonly nickname: string
  }

  export class ExtensionModel {
    readonly name: string
    readonly version: string
    readonly nickname: string
    readonly enabled: string[]

    static list(): Promise<ExtensionModel[]>
    static get(name: string): Promise<ExtensionModel | null>
    static install(input: ExtensionInstallInput): Promise<ExtensionModel>

    changeVersion(version: string, nickname: string): Promise<ExtensionModel>
    updateConfig(config: Record<string, unknown>): Promise<ExtensionModel>
    uninstall(): Promise<void>
    enablePeer(peerId: string): Promise<ExtensionModel>
    disablePeer(peerId: string): Promise<ExtensionModel>
  }
}
