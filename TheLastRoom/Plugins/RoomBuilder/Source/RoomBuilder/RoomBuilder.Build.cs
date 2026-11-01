using UnrealBuildTool;
public class RoomBuilder : ModuleRules {
 public RoomBuilder(ReadOnlyTargetRules Target):base(Target) {
 PCHUsage=PCHUsageMode.UseExplicitOrSharedPCHs;
 PublicDependencyModuleNames.AddRange(new[]{"Core","CoreUObject","Engine","UnrealEd","BlueprintGraph","Kismet","KismetCompiler","InputCore"});
 }
}
