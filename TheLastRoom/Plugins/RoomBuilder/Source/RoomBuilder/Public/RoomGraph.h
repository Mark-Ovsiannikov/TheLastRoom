#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "RoomGraph.generated.h"
class UBlueprint;
class UEdGraph;
class UK2Node;
class UActorComponent;
UCLASS()
class ROOMBUILDER_API URoomGraph : public UBlueprintFunctionLibrary {
 GENERATED_BODY()
public:
 UFUNCTION(BlueprintCallable) static UK2Node* Node(UBlueprint* BP, UEdGraph* Graph, const FString& Kind, const FString& Name, UClass* Owner, int32 X, int32 Y);
 UFUNCTION(BlueprintCallable) static UActorComponent* Component(UBlueprint* BP, UClass* Type, FName Name, FName Parent);
 UFUNCTION(BlueprintCallable) static bool Connect(UK2Node* A, FName Out, UK2Node* B, FName In);
 UFUNCTION(BlueprintCallable) static bool Literal(UK2Node* Node, FName Pin, const FString& Value);
 UFUNCTION(BlueprintCallable) static TArray<FString> Pins(UK2Node* Node);
 UFUNCTION(BlueprintCallable) static int32 RepairInput(UBlueprint* BP);
 UFUNCTION(BlueprintCallable) static void FeedKey(class APlayerController* PC, FName Key, bool Pressed, float Amount);
};
