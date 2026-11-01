#include "RoomGraph.h"
#include "Modules/ModuleManager.h"
#include "Engine/Blueprint.h"
#include "Engine/SimpleConstructionScript.h"
#include "Engine/SCS_Node.h"
#include "EdGraphSchema_K2.h"
#include "K2Node_CallFunction.h"
#include "K2Node_Event.h"
#include "K2Node_CustomEvent.h"
#include "K2Node_InputKey.h"
#include "K2Node_InputAxisKeyEvent.h"
#include "K2Node_InputAxisEvent.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "K2Node_IfThenElse.h"
#include "K2Node_DynamicCast.h"
#include "K2Node_Self.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "GameFramework/PlayerController.h"
#include "InputKeyEventArgs.h"
IMPLEMENT_MODULE(FDefaultModuleImpl, RoomBuilder)
UK2Node* URoomGraph::Node(UBlueprint* BP, UEdGraph* G, const FString& Kind, const FString& Name, UClass* Owner, int32 X,int32 Y) {
 UK2Node* N=nullptr;
 if(Kind=="call") { auto* T=NewObject<UK2Node_CallFunction>(G); UFunction* F=(Owner?Owner:BP->SkeletonGeneratedClass.Get())->FindFunctionByName(*Name); if(!F){UE_LOG(LogTemp,Error,TEXT("Missing function %s"),*Name);return nullptr;} T->SetFromFunction(F);N=T; }
 else if(Kind=="event") {auto* T=NewObject<UK2Node_Event>(G);T->EventReference.SetExternalMember(*Name,Owner);T->bOverrideFunction=true;N=T;}
 else if(Kind=="custom") {auto* T=NewObject<UK2Node_CustomEvent>(G);T->CustomFunctionName=*Name;N=T;}
 else if(Kind=="key") {auto* T=NewObject<UK2Node_InputKey>(G);T->InputKey=FKey(*Name);N=T;}
 else if(Kind=="axis") {auto* T=NewObject<UK2Node_InputAxisKeyEvent>(G);T->Initialize(FKey(*Name));N=T;}
 else if(Kind=="axisname") {auto* T=NewObject<UK2Node_InputAxisEvent>(G);T->Initialize(*Name);N=T;}
 else if(Kind=="get") {auto* T=NewObject<UK2Node_VariableGet>(G);if(Owner)T->VariableReference.SetExternalMember(*Name,Owner);else T->VariableReference.SetSelfMember(*Name);N=T;}
 else if(Kind=="set") {auto* T=NewObject<UK2Node_VariableSet>(G);if(Owner)T->VariableReference.SetExternalMember(*Name,Owner);else T->VariableReference.SetSelfMember(*Name);N=T;}
 else if(Kind=="branch") N=NewObject<UK2Node_IfThenElse>(G);
 else if(Kind=="cast") {auto* T=NewObject<UK2Node_DynamicCast>(G);T->TargetType=Owner;T->SetPurity(true);N=T;}
 else if(Kind=="self") N=NewObject<UK2Node_Self>(G);
 if(!N)return nullptr;
 G->AddNode(N,false,false);N->CreateNewGuid();N->PostPlacedNewNode();N->AllocateDefaultPins();N->NodePosX=X;N->NodePosY=Y;FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);return N;
}
UActorComponent* URoomGraph::Component(UBlueprint* BP,UClass* Type,FName Name,FName Parent){
 USCS_Node* N=BP->SimpleConstructionScript->CreateNode(Type,Name);
 USCS_Node* P=nullptr;for(auto* I:BP->SimpleConstructionScript->GetAllNodes())if(I->GetVariableName()==Parent)P=I;
 if(P)P->AddChildNode(N);else BP->SimpleConstructionScript->AddNode(N);
 FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);return N->ComponentTemplate;
}
bool URoomGraph::Connect(UK2Node* A,FName Out,UK2Node* B,FName In){if(!A||!B)return false;auto* P=A->FindPin(Out,EGPD_Output);auto* Q=B->FindPin(In,EGPD_Input);return P&&Q&&GetDefault<UEdGraphSchema_K2>()->TryCreateConnection(P,Q);}
bool URoomGraph::Literal(UK2Node* N,FName Pin,const FString& V){if(!N)return false;auto* P=N->FindPin(Pin,EGPD_Input);if(!P)return false;GetDefault<UEdGraphSchema_K2>()->TrySetDefaultValue(*P,V);return true;}
TArray<FString> URoomGraph::Pins(UK2Node* N){TArray<FString> A;if(N)for(auto* P:N->Pins)A.Add(FString::Printf(TEXT("%s %s [%s] %s"),P->Direction==EGPD_Input?TEXT("IN"):TEXT("OUT"),*P->PinName.ToString(),*P->PinType.PinCategory.ToString(),*P->DefaultValue));return A;}
int32 URoomGraph::RepairInput(UBlueprint* BP){
 int32 Count=0;TArray<UEdGraph*> Graphs;BP->GetAllGraphs(Graphs);
 for(auto* G:Graphs)for(auto& NodePtr:G->Nodes){auto* N=NodePtr.Get();
  if(auto* A=Cast<UK2Node_InputAxisKeyEvent>(N)){A->Initialize(A->AxisKey);++Count;}
  if(auto* A=Cast<UK2Node_InputAxisEvent>(N)){A->Initialize(A->InputAxisName);++Count;}
 }
 FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);return Count;
}
void URoomGraph::FeedKey(APlayerController* PC,FName Key,bool Pressed,float Amount){
 if(!PC)return;FKey K(Key);
 PC->InputKey(FInputKeyEventArgs::CreateSimulated(K,K.IsAxis1D()?IE_Axis:(Pressed?IE_Pressed:IE_Released),Amount,1));
}
