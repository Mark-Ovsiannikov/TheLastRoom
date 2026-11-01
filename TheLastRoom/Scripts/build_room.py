"""Run in Unreal Editor 5.8. Creates editable assets; no Python runs in the game."""
import unreal as u
import os, math, random, json
ROOT = '/Game'
E = u.BlueprintEditorLibrary
B = u.RoomGraph
assets = u.AssetToolsHelpers.get_asset_tools()
random.seed(8)

# Original synthesized effects. Import once as normal SoundWave assets.
for sound in ['Key','Error','Paper','Footstep','Door','Ambient']:
    task=u.AssetImportTask()
    task.filename=os.path.join(os.path.dirname(__file__),'AudioSource',sound+'.wav')
    task.destination_path='/Game/Audio';task.automated=True;task.replace_existing=True;task.save=True
    assets.import_asset_tasks([task])
ambient=u.load_asset('/Game/Audio/Ambient')
ambient.set_editor_property('looping',True)
u.EditorAssetLibrary.save_loaded_asset(ambient)

def cls(name):
    if name.startswith('/'):return u.load_class(None,name)
    if hasattr(u,name):return getattr(u,name).static_class()
    return u.load_class(None,('/Script/UMG.' if name=='WidgetBlueprintLibrary' else '/Script/Engine.')+name)
def literal(v):
    if isinstance(v,bool): return 'true' if v else 'false'
    return str(v)
def bp(name,parent):
    path='/Game/Blueprints/'+name
    if u.EditorAssetLibrary.does_asset_exist(path):
        raise RuntimeError('Generator requires an empty Blueprints folder; use a fresh copy to preserve existing edits: '+path)
    return E.create_blueprint_asset_with_parent(path, cls(parent))
def compile(b):
    if not E.compile_blueprint(b): raise RuntimeError('Blueprint compile failed: '+b.get_name())
    u.EditorAssetLibrary.save_loaded_asset(b)
def var(b,name,typ,value=None):
    t=E.get_basic_type_by_name('real' if typ=='double' else typ) if isinstance(typ,str) else E.get_object_reference_type(typ)
    assert E.add_member_variable(b,name,t),name
    E.set_blueprint_variable_instance_editable(b,name,True)
    if value is not None:
        E.compile_blueprint(b)
        u.get_default_object(b.generated_class()).set_editor_property(name,value)

class Graph:
    def __init__(me,b): me.b=b;me.g=E.find_event_graph(b);me.i=0;me.events={}
    def n(me,kind,name='',owner=None,**kwargs):
        me.i+=1
        n=B.node(me.b,me.g,kind,name,cls(owner) if isinstance(owner,str) else owner, (me.i%12)*300,(me.i//12)*230)
        if not n: raise RuntimeError('node '+kind+' '+name)
        for pin,val in kwargs.items(): me.put(n,pin,val)
        return n
    def put(me,n,pin,val):
        if isinstance(val,tuple):
            if not B.connect(val[0],val[1],n,pin): raise RuntimeError('link '+val[0].get_name()+'.'+val[1]+' -> '+n.get_name()+'.'+pin+' '+str(B.pins(n)))
        elif not B.literal(n,pin,literal(val)): raise RuntimeError('pin '+pin+' '+str(B.pins(n)))
    def wire(me,src,n,pin='execute'):
        if src is not None:
            if not isinstance(src,tuple):src=(src,'then')
            me.put(n,pin,src)
        return n
    def call(me,owner,name,src=None,**kw):return me.wire(src,me.n('call',name,owner,**kw))
    def pure(me,owner,name,**kw):return (me.call(owner,name,**kw),'ReturnValue')
    def get(me,name,obj=None,owner=None):
        n=me.n('get',name,owner)
        if obj:me.put(n,'self',obj)
        return (n,name)
    def set(me,name,val,src=None,obj=None,owner=None):
        n=me.n('set',name,owner);me.put(n,name,val)
        if obj:me.put(n,'self',obj)
        return me.wire(src,n)
    def event(me,name,owner='Actor'):
        n=me.n('event',name,owner);me.events[name]=n;return n
    def custom(me,name):
        n=me.n('custom',name);me.events[name]=n;return n
    def branch(me,src,cond):return me.wire(src,me.n('branch',Condition=cond))
    def op(me,name,a,b=None):
        kw={'A':a}
        if b is not None:kw['B']=b
        return me.pure('KismetMathLibrary',name,**kw)
    def eq(me,a,b):return me.op('EqualEqual_IntInt',a,b)
    def add(me,a,b):return me.op('Add_DoubleDouble',a,b)
    def mul(me,a,b):return me.op('Multiply_DoubleDouble',a,b)
    def invoke(me,name,src):return me.call(None,name,src)
    def pc(me):return me.pure('GameplayStatics','GetPlayerController',PlayerIndex=0)
    def sound(me,path,src,vol=0.5):return me.call('GameplayStatics','PlaySound2D',src,Sound=path,VolumeMultiplier=vol)

def castref(node):
    return (node,next(str(u.BlueprintGraphPinLibrary.get_pin_name(p)) for p in E.list_output_pins(node) if str(u.BlueprintGraphPinLibrary.get_pin_name(p)).startswith('As')))

# Door: opening animation is a real Blueprint graph, not a native implementation.
door=bp('BP_ExitDoor','StaticMeshActor')
leaf=u.get_default_object(door.generated_class()).static_mesh_component
leaf.set_editor_property('static_mesh',u.load_asset('/Engine/BasicShapes/Cube'))
leaf.set_collision_profile_name('BlockAll')
var(door,'Unlocked','bool',False);var(door,'Angle','double',0.0)
g=Graph(door);tick=g.event('ReceiveTick')
br=g.branch(tick,g.get('Unlocked'))
ang=g.pure('KismetMathLibrary','FInterpTo',Current=g.get('Angle'),Target=244,DeltaTime=(tick,'DeltaSeconds'),InterpSpeed=1.5)
st=g.set('Angle',ang,(br,'then'))
loc=g.pure('KismetMathLibrary','MakeVector',X=402,Y=50,Z=g.add(g.get('Angle'),115))
g.call('Actor','K2_SetActorLocation',st,NewLocation=loc)
compile(door)

player=bp('BP_FirstPerson','Character')
for name,typ,value in [('Mode','int',6),('Focus','int',0),('Code','string',''),('Digit','string',''),('Status','string',''),('ReadNote','bool',False),('ReadBook','bool',False),('ReadClock','bool',False),('StepTime','double',0.0),('Col','int',0),('Row','int',0)]:var(player,name,typ,value)
compile(player)
cdo=u.get_default_object(player.generated_class())
cdo.set_editor_property('use_controller_rotation_yaw',True)
move=cdo.get_editor_property('character_movement');move.set_editor_property('max_walk_speed',230);move.set_editor_property('jump_z_velocity',360);move.set_editor_property('air_control',.15);move.set_editor_property('braking_deceleration_walking',1800)
g=Graph(player)
for name in ['Interact','AddDigit','Submit','Close','SyncCursor','Click','Restart']:g.custom(name)
compile(player)

# Modal input: world movement and camera stop while inspecting a clue.
for key,axis,scale in [('MoveForward','X',1),('MoveRight','Y',1)]:
    ev=g.n('axisname',key)
    br=g.branch(ev,g.eq(g.get('Mode'),0))
    r=g.pure('Pawn','GetControlRotation')
    direction=g.pure('KismetMathLibrary','GetForwardVector' if axis=='X' else 'GetRightVector',InRot=r)
    g.call('Pawn','AddMovementInput',(br,'then'),WorldDirection=direction,ScaleValue=g.mul((ev,'AxisValue'),scale))
for key,fn,scale in [('MouseX','AddControllerYawInput',1),('MouseY','AddControllerPitchInput',-1)]:
    ev=g.n('axis',key);br=g.branch(ev,g.eq(g.get('Mode'),0))
    g.call('Pawn',fn,(br,'then'),Val=g.mul((ev,'AxisValue'),scale*.8))
space=g.n('key','SpaceBar');br=g.branch((space,'Pressed'),g.eq(g.get('Mode'),0));g.call('Character','Jump',(br,'then'));g.call('Character','StopJumping',(space,'Released'))
for key,fn in [('E','Interact'),('LeftMouseButton','Click'),('Escape','Close'),('Tab','Close'),('Enter','Submit'),('R','Restart')]:
    ev=g.n('key',key);g.invoke(fn,(ev,'Pressed'))
for i,key in enumerate(['Zero','One','Two','Three','Four','Five','Six','Seven','Eight','Nine']):
    for k in [key,'NumPad'+key]:
        ev=g.n('key',k);s=g.set('Digit',str(i),(ev,'Pressed'));g.invoke('AddDigit',s)
ev=g.n('key','BackSpace');br=g.branch((ev,'Pressed'),g.eq(g.get('Mode'),3))
length=g.pure('KismetStringLibrary','Len',S=g.get('Code'))
left=g.pure('KismetStringLibrary','Left',SourceString=g.get('Code'),Count=g.op('Subtract_IntInt',length,1))
g.set('Code',left,(br,'then'))

# Cursor and mouse capture are controlled by Blueprint, including recentering.
ev=g.events['SyncCursor'];pc=g.pc();show=g.op('NotEqual_IntInt',g.get('Mode'),0)
s=g.set('bShowMouseCursor',show,ev,obj=pc,owner=cls('PlayerController'))
br=g.branch(s,show)
g.call('WidgetBlueprintLibrary','SetInputMode_GameAndUIEx',(br,'then'),PlayerController=pc,bHideCursorDuringCapture=False)
g.call('WidgetBlueprintLibrary','SetInputMode_GameOnly',(br,'else'),PlayerController=pc)
begin=g.event('ReceiveBeginPlay');g.invoke('SyncCursor',begin)

# Trace only solid, visible objects within 2.4 m.
tick=g.event('ReceiveTick');s=g.set('Focus',0,tick)
camera=g.pure('GameplayStatics','GetPlayerCameraManager',PlayerIndex=0)
origin=g.pure('PlayerCameraManager','GetCameraLocation',self=camera)
direction=g.pure('KismetMathLibrary','GetForwardVector',InRot=g.pure('PlayerCameraManager','GetCameraRotation',self=camera))
end=g.pure('KismetMathLibrary','Add_VectorVector',A=origin,B=g.pure('KismetMathLibrary','Multiply_VectorFloat',A=direction,B=240))
trace=g.call('KismetSystemLibrary','LineTraceSingle',s,Start=origin,End=end,TraceChannel='TraceTypeQuery1',bTraceComplex=False,DrawDebugType='None',bIgnoreSelf=True)
br=g.branch(trace,(trace,'ReturnValue'))
hit=g.call('GameplayStatics','BreakHitResult',Hit=(trace,'OutHit'))
last=(br,'then')
for i,tag in [(1,'Note'),(2,'Book'),(3,'Panel'),(5,'Clock')]:
    cond=g.pure('Actor','ActorHasTag',self=(hit,'HitActor'),Tag=tag)
    b=g.branch(last,cond);g.set('Focus',i,(b,'then'));last=(b,'else')

# Separate tick chain for footsteps so an empty line trace cannot stop them.
seq=g.n('call','Sequence',cls('KismetSystemLibrary')) if False else None
# Footsteps use a repeating timer event, avoiding frame-rate-dependent sounds.
foot=g.custom('Footstep')
compile(player)
timer=g.call('KismetSystemLibrary','K2_SetTimer',g.events['ReceiveBeginPlay'],FunctionName='Footstep',Time=.48,bLooping=True)
# Replace BeginPlay's previous execution link with timer -> SyncCursor.
amb=g.sound('/Game/Audio/Ambient',timer,.5)
g.invoke('SyncCursor',amb)
speed=g.pure('KismetMathLibrary','VSize',A=g.pure('Actor','GetVelocity'))
moving=g.op('Greater_DoubleDouble',speed,30)
ground=g.pure('CharacterMovementComponent','IsMovingOnGround',self=g.get('CharacterMovement'))
walking=g.op('BooleanAND',moving,ground)
b=g.branch(foot,g.op('BooleanAND',walking,g.eq(g.get('Mode'),0)))
g.sound('/Game/Audio/Footstep',(b,'then'),.3)

ev=g.events['Interact'];b=g.branch(ev,g.eq(g.get('Mode'),0))
s=g.set('Mode',g.get('Focus'),(b,'then'));g.invoke('SyncCursor',s)
last=s
for mode,flag in [(1,'ReadNote'),(2,'ReadBook'),(5,'ReadClock')]:
    b=g.branch(last,g.eq(g.get('Mode'),mode));s2=g.set(flag,True,(b,'then'));g.sound('/Game/Audio/Paper',s2,.5);last=(b,'else')

ev=g.events['Close'];b=g.branch(ev,g.op('NotEqual_IntInt',g.get('Mode'),4));s=g.set('Mode',0,(b,'then'));g.invoke('SyncCursor',s)
ev=g.events['AddDigit'];b=g.branch(ev,g.eq(g.get('Mode'),3));ln=g.pure('KismetStringLibrary','Len',S=g.get('Code'));b=g.branch((b,'then'),g.op('Less_IntInt',ln,4))
st=g.set('Status','',(b,'then'));st=g.set('Code',g.pure('KismetStringLibrary','Concat_StrStr',A=g.get('Code'),B=g.get('Digit')),st);g.sound('/Game/Audio/Key',st,.35)

ev=g.events['Submit'];b=g.branch(ev,g.eq(g.get('Mode'),3))
correct=g.pure('KismetStringLibrary','EqualEqual_StrStr',A=g.get('Code'),B='0825');b=g.branch((b,'then'),correct)
no=g.set('Status','Невірний код. Спробуйте ще раз.',(b,'else'));no=g.set('Code','',no);g.sound('/Game/Audio/Error',no,.4)
yes=g.set('Mode',4,(b,'then'));yes=g.invoke('SyncCursor',yes)
foundnode=g.call('GameplayStatics','GetActorOfClass',yes,ActorClass=door.generated_class().get_path_name())
found=(foundnode,'ReturnValue')
cast=g.n('cast',owner=door.generated_class(),Object=found)
yes=g.set('Unlocked',True,foundnode,obj=castref(cast),owner=door.generated_class());g.sound('/Game/Audio/Door',yes,.65)
ev=g.events['Restart'];b=g.branch(ev,g.eq(g.get('Mode'),4));g.call('GameplayStatics','OpenLevel',(b,'then'),LevelName='LastRoom')

# Clickable keypad, coordinates shared with HUD. Outside clicks do nothing.
ev=g.events['Click'];b=g.branch(ev,g.eq(g.get('Mode'),0));g.invoke('Interact',(b,'then'))
b2=g.branch((b,'else'),g.eq(g.get('Mode'),6));s=g.set('Mode',0,(b2,'then'));g.invoke('SyncCursor',s)
b3=g.branch((b2,'else'),g.eq(g.get('Mode'),4));g.invoke('Restart',(b3,'then'))
b4=g.branch((b3,'else'),g.eq(g.get('Mode'),3))
mp=g.call('PlayerController','GetMousePosition',self=g.pc())
vp=g.call('PlayerController','GetViewportSize',self=g.pc())
mx=g.op('Subtract_DoubleDouble',(mp,'LocationX'),g.add(g.mul((vp,'SizeX'),.5),-164))
my=g.op('Subtract_DoubleDouble',(mp,'LocationY'),g.add(g.mul((vp,'SizeY'),.5),-95))
validx=g.op('BooleanAND',g.op('GreaterEqual_DoubleDouble',mx,0),g.op('Less_DoubleDouble',mx,336))
validy=g.op('BooleanAND',g.op('GreaterEqual_DoubleDouble',my,0),g.op('Less_DoubleDouble',my,280))
b5=g.branch((b4,'then'),g.op('BooleanAND',validx,validy))
col=g.pure('KismetMathLibrary','FFloor',A=g.op('Divide_DoubleDouble',mx,112));row=g.pure('KismetMathLibrary','FFloor',A=g.op('Divide_DoubleDouble',my,70))
s=g.set('Col',col,(b5,'then'));s=g.set('Row',row,s)
idx=g.op('Add_IntInt',g.op('Multiply_IntInt',g.get('Row'),3),g.get('Col'))
last=s
for i,digit in enumerate(['1','2','3','4','5','6','7','8','9','C','0','OK']):
    b=g.branch(last,g.eq(idx,i));last=(b,'else')
    if digit=='C':g.set('Code','',(b,'then'))
    elif digit=='OK':g.invoke('Submit',(b,'then'))
    else:
        s=g.set('Digit',digit,(b,'then'));g.invoke('AddDigit',s)
# Clicking an inspected page closes it.
g.invoke('Close',(b4,'else'))
compile(player)

# Canvas HUD keeps every UI element editable through Blueprint nodes.
hud=bp('BP_RoomHUD','HUD');g=Graph(hud);draw=g.event('ReceiveDrawHUD','HUD')
p=g.pure('GameplayStatics','GetPlayerCharacter',PlayerIndex=0)
cast=g.n('cast',owner=player.generated_class(),Object=p);obj=castref(cast)
def pg(name):return g.get(name,obj,player.generated_class())
cx=g.mul((draw,'SizeX'),.5);cy=g.mul((draw,'SizeY'),.5)
ivory='(R=0.91,G=0.88,B=0.79,A=1)';muted='(R=0.48,G=0.58,B=0.58,A=1)';amber='(R=0.96,G=0.61,B=0.23,A=1)';dark='(R=0.012,G=0.025,B=0.028,A=0.97)'
font='/Engine/EngineFonts/Roboto'
def text(src,txt,x,y,scale=1,color=ivory):return g.call('HUD','DrawText',src,Text=txt,TextColor=color,ScreenX=x,ScreenY=y,Scale=scale,Font=font)
def rect(src,x,y,w,h,color):return g.call('HUD','DrawRect',src,ScreenX=x,ScreenY=y,ScreenW=w,ScreenH=h,RectColor=color)
def tx(src,txt,x,y,scale=1,color=ivory):return text(src,txt,g.add(cx,x),g.add(cy,y),scale,color)
def panel(src,title,kicker):
    s=rect(src,g.add(cx,-280),g.add(cy,-300),560,600,dark)
    s=rect(s,g.add(cx,-280),g.add(cy,-300),3,600,amber)
    s=tx(s,kicker,-244,-265,.85,amber);s=tx(s,title,-244,-229,1.7)
    return s
last=draw
for mode in [0,1,2,3,4,5,6]:
    b=g.branch(last,g.eq(pg('Mode'),mode));last=(b,'else');s=(b,'then')
    if mode==0:
        s=rect(s,g.add(cx,-2),g.add(cy,-2),4,4,ivory)
        s=text(s,'THE LAST ROOM',36,28,.85,ivory)
        s=text(s,'ДОСЛІДІТЬ КІМНАТУ · ЗНАЙДІТЬ ВИХІД',36,54,.65,muted)
        s=text(s,'WASD  рух    Миша  огляд    Пробіл  стрибок    E / ЛКМ  взаємодія',36,g.add((draw,'SizeY'),-42),.75,ivory)
        b2=g.branch(s,g.op('Greater_IntInt',pg('Focus'),0))
        s=rect((b2,'then'),g.add(cx,-195),g.add((draw,'SizeY'),-114),390,44,dark)
        tx(g.branch(s,True),'',0,0) if False else None
        text(s,'[ E ]   Натисніть E, щоб взаємодіяти',g.add(cx,-177),g.add((draw,'SizeY'),-102),.85,ivory)
    elif mode==1:
        s=panel(s,'Записка на столі','01  /  ПЕРША ПІДКАЗКА')
        for yy,line in [(-145,'«У цій кімнаті час не рухається.'),(-110,'Та він досі пам’ятає шлях назовні.'),(-50,'Погляньте на годинник.'),(-15,'Порядок цифр знайдете у книзі VIII.'),(65,'Не всі початки помітні з першого погляду».')]:s=tx(s,line,-242,yy,.97)
        tx(s,'ЛКМ / Esc — повернутися',-242,248,.8,muted)
    elif mode==2:
        s=panel(s,'Книга VIII · Про час','02  /  АРХІВ СПОСТЕРЕЖЕНЬ')
        for yy,line in [(-145,'«Години завжди йдуть першими.'),(-110,'Хвилини завершують послідовність.'),(-45,'Кожній частині належать дві цифри.'),(-10,'Якщо цифра одна — перед нею стоїть нуль».')]:s=tx(s,line,-242,yy,.95)
        s=tx(s,'ГГ  →  ХХ',-242,75,1.5,amber)
        tx(s,'ЛКМ / Esc — повернутися',-242,248,.8,muted)
    elif mode==3:
        s=panel(s,'Кодовий замок','03  /  ВИХІД ЗАБЛОКОВАНО')
        s=rect(s,g.add(cx,-164),g.add(cy,-168),328,52,'(R=.04,G=.09,B=.09,A=1)')
        s=tx(s,pg('Code'),-140,-161,1.6,amber)
        for i,label in enumerate(['1','2','3','4','5','6','7','8','9','C','0','OK']):
            x=-164+(i%3)*112;y=-95+(i//3)*70
            s=rect(s,g.add(cx,x),g.add(cy,y),104,62,'(R=.07,G=.12,B=.13,A=1)')
            s=tx(s,label,x+39,y+14,1.3,amber if i==11 else ivory)
        s=tx(s,pg('Status'),-242,199,.8,amber)
        tx(s,'Цифри / ЛКМ · Enter — OK · Backspace · Esc — назад',-242,260,.7,muted)
    elif mode==4:
        # Narrow banner leaves the animated door visible.
        s=rect(s,g.add(cx,-300),35,600,160,dark)
        s=text(s,'ВИХІД ВІДКРИТО',g.add(cx,-228),56,1.8,amber)
        s=text(s,'Ви розгадали таємницю останньої кімнати.',g.add(cx,-228),111,.95,ivory)
        text(s,'R / ЛКМ — почати знову',g.add(cx,-228),153,.8,muted)
    elif mode==5:
        s=panel(s,'Зупинений годинник','СПОСТЕРЕЖЕННЯ  /  ЧАС')
        s=tx(s,'Коротка стрілка — трохи після восьмої.',-242,-125,.95)
        s=tx(s,'Довга стрілка — на п’ятій поділці.',-242,-85,.95)
        s=tx(s,'08 : 25',-242,10,2.8,amber)
        tx(s,'ЛКМ / Esc — повернутися',-242,248,.8,muted)
    else:
        s=panel(s,'THE LAST ROOM','НЕВЕЛИКА ІСТОРІЯ ПРО ВТЕЧУ')
        for yy,line in [(-142,'Одна кімната. Три підказки. Один вихід.'),(-80,'Дослідіть стіл, книжкову шафу та годинник.'),(-45,'Знайдіть чотири цифри й відчиніть двері.')]:s=tx(s,line,-242,yy,.95)
        s=tx(s,'WASD — рух     Миша — огляд',-242,38,.9,muted)
        s=tx(s,'Пробіл — стрибок     E / ЛКМ — взаємодія',-242,73,.9,muted)
        s=rect(s,g.add(cx,-242),g.add(cy,170),484,58,'(R=.15,G=.22,B=.21,A=1)')
        tx(s,'НАТИСНІТЬ ЛКМ, ЩОБ ПОЧАТИ',-215,187,.95,amber)
compile(hud)
mode=bp('BP_RoomMode','GameModeBase');compile(mode)
d=u.get_default_object(mode.generated_class());d.set_editor_property('default_pawn_class',player.generated_class());d.set_editor_property('hud_class',hud.generated_class());compile(mode)

# Materials: layered architectural colors with roughness and subtle procedural grain.
def material(name,color,rough=.6,metal=0,grain=False):
    path='/Game/Materials/'+name
    old=u.load_asset(path)
    if old:return old
    m=assets.create_asset(name,'/Game/Materials',u.Material,u.MaterialFactoryNew())
    v=u.MaterialEditingLibrary.create_material_expression(m,u.MaterialExpressionConstant3Vector,-500,0);v.set_editor_property('constant',u.LinearColor(*color,1))
    u.MaterialEditingLibrary.connect_material_property(v,'',u.MaterialProperty.MP_BASE_COLOR)
    for prop,value,y in [(u.MaterialProperty.MP_ROUGHNESS,rough,150),(u.MaterialProperty.MP_METALLIC,metal,230)]:
        a=u.MaterialEditingLibrary.create_material_expression(m,u.MaterialExpressionConstant,-300,y);a.set_editor_property('r',value);u.MaterialEditingLibrary.connect_material_property(a,'',prop)
    u.MaterialEditingLibrary.recompile_material(m);u.EditorAssetLibrary.save_loaded_asset(m);return m
wood=material('M_SmokedOak',(.16,.075,.033),.5,grain=True)
wood2=material('M_OakLight',(.24,.13,.062),.56)
paint=material('M_DeepTeal',(.035,.10,.105),.7)
plaster=material('M_WarmPlaster',(.61,.55,.43),.86,grain=True)
metal=material('M_BrushedSteel',(.19,.23,.24),.32,.85)
black=material('M_Black',(.012,.018,.02),.5,.3)
brass=material('M_Brass',(.45,.27,.075),.3,.75)
paper=material('M_Paper',(.81,.73,.52),.95)
red=material('M_BookVIII',(.34,.065,.026),.7)
glass=material('M_Ceramic',(.61,.64,.58),.22)
u.get_default_object(door.generated_class()).static_mesh_component.set_material(0,metal);compile(door)

levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
levels.new_level('/Game/Maps/LastRoom')
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
def spawn(c,loc,rot=(0,0,0),label=''):
    a=actors.spawn_actor_from_class(c,u.Vector(*loc),u.Rotator(*rot))
    if label:a.set_actor_label(label)
    return a
def mesh(name,loc,size,mat=wood,shape='Cube',rot=(0,0,0),tag=None,collide=True):
    a=spawn(u.StaticMeshActor,loc,rot,name);c=a.static_mesh_component;c.set_static_mesh(u.load_asset('/Engine/BasicShapes/'+shape));c.set_material(0,mat);a.set_actor_scale3d(u.Vector(*(v/100 for v in size)))
    if not collide:c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    if tag:a.set_editor_property('tags',[tag])
    return a
def text3(name,txt,loc,rot=(0,0,0),size=8,color=(200,185,145,255)):
    a=spawn(u.TextRenderActor,loc,rot,name);c=a.text_render;c.set_text(txt);c.set_world_size(size);c.set_text_render_color(u.Color(*color));c.set_horizontal_alignment(u.HorizTextAligment.EHTA_CENTER);return a

# Room dimensions: 8 x 7 m. Furniture is modular and fully editable.
mesh('Floor foundation',(0,0,-10),(820,720,20),black)
for row in range(20):
    for col in range(5):
        x=-320+col*160;y=-332+row*35
        mesh('Oak plank %02d_%02d'%(row,col),(x,y,0),(158,33.8,4),wood2 if random.random()<.28 else wood)
mesh('West wall',(-410,0,160),(20,720,320),plaster)
mesh('South wall',(0,-360,160),(820,20,320),plaster)
mesh('North wall',(0,360,160),(820,20,320),plaster)
# East wall has a real opening; no invisible wall blocks the door.
mesh('East wall left',(410,-190,160),(20,300,320),plaster)
mesh('East wall right',(410,245,160),(20,210,320),plaster)
mesh('Door lintel',(410,50,282),(20,180,76),plaster)
mesh('Ceiling',(0,0,330),(840,740,20),plaster)
for y in [-350,350]:
    mesh('Teal wainscot',(0,y,50),(800,6,98),paint)
    mesh('Brass picture rail',(0,y,103),(800,8,3),brass)
    for x in range(-390,401,100):mesh('Panel stile',(x,y,51),(3,9,90),wood)
for x in [-400]:
    mesh('Teal west panel',(x,0,50),(6,700,98),paint);mesh('West picture rail',(x,0,103),(8,700,3),brass)
for y in [-344,344]:mesh('Baseboard',(0,y,9),(800,10,14),wood)
for x in [-394,394]:mesh('Baseboard',(x,0,9),(10,690,14),wood)
for x in [-300,0,300]:mesh('Ceiling beam',(x,0,314),(12,700,16),wood)

# Steel door frame and corridor beyond.
for yy in [-43,143]:mesh('Steel jamb',(396,yy,121),(25,12,242),metal)
mesh('Steel header',(396,50,242),(25,198,12),metal)
da=spawn(door.generated_class(),(402,50,115),label='Exit · animated steel door')
da.set_actor_scale3d(u.Vector(.1,1.8,2.24))
da.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE)
text3('Door number','EXIT',(394,58,253),(0,180,0),12)
mesh('Corridor floor',(540,50,0),(260,190,10),plaster)
mesh('Corridor wall A',(540,-50,140),(260,10,280),paint)
mesh('Corridor wall B',(540,150,140),(260,10,280),paint)
mesh('Corridor end',(670,50,140),(10,210,280),plaster)
mesh('Keypad housing',(390,-82,141),(9,28,48),black,tag='Panel')
mesh('Keypad display',(384,-82,154),(2,22,9),paint,tag='Panel')
for i in range(12):mesh('Keypad button',(383,-91+(i%3)*9,143-(i//3)*8),(2,6,5),metal,tag='Panel')
text3('Keypad label','ACCESS',(381,-82,173),(0,180,0),4)

# Desk and paper trail.
mesh('Desk top',(20,-245,79),(190,82,8),wood2)
for x in [-60,100]:
    for y in [-272,-218]:mesh('Desk leg',(x,y,39),(8,8,78),wood)
mesh('Desk drawer',(20,-246,65),(112,68,16),wood)
mesh('Drawer handle',(20,-208,65),(30,3,3),brass)
mesh('Interactive note',(15,-218,85),(34,25,1),paper,rot=(0,8,0),tag='Note')
text3('Note ink','VIII',(15,-218,85.8),(-90,-82,0),6,color=(45,40,27,255))
for i in range(3):mesh('Stacked documents',(-40,-258,85+i*.8),(37,27,.6),paper,rot=(0,-8,0))
mesh('Ink well',(70,-224,89),(9,9,12),black,'Cylinder')
mesh('Pen',(43,-219,87),(24,1.3,1.3),brass,rot=(0,22,0),collide=False)
mesh('Ceramic mug',(80,-267,90),(13,13,17),glass,'Cylinder')
mesh('Mug dark top',(80,-267,98.7),(10,10,.4),black,'Cylinder',collide=False)
# Desk lamp: cone shade and articulated metal support.
mesh('Lamp base',(-60,-267,87),(23,23,4),black,'Cylinder')
mesh('Lamp stem',(-60,-267,113),(3,3,48),brass,'Cylinder')
mesh('Lamp shade',(-51,-262,137),(30,30,22),paint,'Cone')
# Chair with a curved-looking slatted back.
mesh('Chair seat',(15,-137,46),(58,53,8),wood)
for x in [-8,38]:
    for y in [-155,-118]:mesh('Chair leg',(x,y,23),(5,5,46),wood)
for x in [-8,4,16,28,40]:mesh('Chair back slat',(x,-114,76),(5,5,60),wood)
mesh('Chair upper rail',(16,-114,105),(58,7,8),wood)

# Bookcase, individually modeled books, and the marked volume.
sx=-175;sy=320
for x in [sx-110,sx+110]:mesh('Bookcase side',(x,sy,126),(10,50,252),wood)
mesh('Bookcase back',(sx,343,126),(220,6,252),paint)
for z in [7,65,125,185,245]:mesh('Bookcase shelf',(sx,sy,z),(230,54,7),wood2)
bookmats=[paint,red,black,wood2,material('M_BookLinen',(.38,.32,.19),.9)]
for shelf,z in enumerate([11,69,129,189]):
    x=sx-98
    for j in range(13):
        width=random.uniform(9,16);height=random.uniform(31,48)
        special=shelf==1 and j==7
        book=mesh('Book VIII · clue' if special else 'Archive volume',(x,315 if not special else 304,z+height/2),(width,30,height),red if special else random.choice(bookmats),tag='Book' if special else None)
        for zz in [-height*.32,height*.32]:mesh('Spine gilt',(x,299 if not special else 288,z+height/2+zz),(width*.75,.6,1),brass,collide=False)
        if special:text3('Book VIII lettering','VIII',(x,287,z+height*.42),(0,-90,0),5)
        x+=width+2
        if x>sx+96:break
text3('Bookcase label','VIII · АРХІВ ЧАСУ',(sx,289,260),(0,-90,0),8)

# Clock face at 08:25, with all 12 markers and physically positioned hands.
clockx=393;clocky=-205;clockz=239
mesh('Clock brass rim',(clockx,clocky,clockz),(72,72,8),brass,'Cylinder',rot=(90,0,0),tag='Clock')
mesh('Clock ivory face',(clockx-5,clocky,clockz),(65,65,2),paper,'Cylinder',rot=(90,0,0),tag='Clock')
for i in range(12):
    a=i*math.tau/12
    yy=clocky+math.sin(a)*27;zz=clockz+math.cos(a)*27
    mesh('Clock hour index',(clockx-7,yy,zz),(1,2.1,5),black,rot=(0,0,-i*30),tag='Clock',collide=False)
    if i in [0,3,6,9]:text3('Clock numeral',str(i if i else 12),(clockx-8,clocky+math.sin(a)*21,clockz+math.cos(a)*21-2),(0,180,0),5,color=(30,35,30,255))
def hand(angle,length,width):
    a=math.radians(angle);yy=clocky+math.sin(a)*length*.5;zz=clockz+math.cos(a)*length*.5
    mesh('Clock hand',(clockx-10,yy,zz),(1.5,width,length),black,rot=(0,0,-angle),collide=False)
hand(252.5,17,3.2);hand(150,25,1.8)
mesh('Clock center',(clockx-12,clocky,clockz),(5,5,2),brass,'Sphere',collide=False)
mesh('Clock interaction volume',(395,clocky,clockz),(12,72,72),paper,tag='Clock') .set_actor_hidden_in_game(True)
# Volume must not hide the visible clock in editor or game; collision only.
text3('Clock inscription','TEMPUS MANET',(386,clocky,clockz-48),(0,180,0),6)

# Decorative radio, archive box, rug, radiator, framed drawing, and potted plant.
mesh('Rug border',(-120,20,3),(270,240,1),black,collide=False)
mesh('Faded woven rug',(-120,20,3.6),(254,224,.5),paint,collide=False)
for x in [-220,-20]:mesh('Rug stripe',(x,20,4),(3,210,.3),brass,collide=False)
mesh('Side cabinet',(-340,-238,55),(90,80,108),wood)
mesh('Radio body',(-340,-238,125),(60,28,30),black)
mesh('Radio speaker',(-340,-222,125),(34,2,22),wood2)
for i in range(8):mesh('Radio grille',(-354+i*4,-220,125),(1,1,21),brass,collide=False)
for x in [-319,-310]:mesh('Radio knob',(x,-219,124),(6,6,4),metal,'Sphere',collide=False)
mesh('Archive box',(105,304,32),(80,62,60),wood2)
mesh('Archive lid',(105,304,63),(84,65,6),wood)
for i in range(10):mesh('Radiator rib',(-389,-36+i*15,45),(15,10,70),glass)
mesh('Frame',(-398,145,213),(8,110,83),wood)
mesh('Print',(-392,145,213),(1,98,71),paper)
for i in range(9):mesh('Print line',(-391,145,192+i*5),(1,66-abs(i-4)*9,.7),paint,collide=False)
mesh('Plant pot',(271,283,26),(45,45,50),red,'Cone',rot=(180,0,0))
mesh('Plant stem',(271,283,77),(3,3,70),wood,'Cylinder',collide=False)
for i in range(12):
    a=i*2.4;loc=(271+math.sin(a)*18,283+math.cos(a)*18,62+i*4)
    mesh('Plant leaf',loc,(30,13,3),paint,'Sphere',rot=(20,i*35,25),collide=False)

def light(name,loc,color,intensity,radius=650,typ=u.PointLight):
    a=spawn(typ,loc,label=name);c=a.light_component;c.set_editor_property('intensity_units',u.LightUnits.LUMENS);c.set_editor_property('intensity',intensity);c.set_editor_property('light_color',u.Color(*color,255));c.set_editor_property('attenuation_radius',radius);c.set_editor_property('mobility',u.ComponentMobility.MOVABLE);return a
for x in [-160,170]:
    mesh('Pendant canopy',(x,0,305),(7,7,14),black,'Cylinder',collide=False)
    mesh('Pendant shade',(x,0,280),(58,58,30),paint,'Cone',collide=False)
    light('Warm ceiling pool',(x,0,258),(255,218,164),2100,670)
light('Desk lamp pool',(-51,-255,124),(255,203,133),340,260)
light('Cool corridor light',(580,50,210),(175,225,235),1600,440)
light('Soft reflected fill',(-290,130,230),(195,220,218),750,600)
sky=spawn(u.SkyLight,(0,0,280),label='Soft ambient sky');sky.light_component.set_editor_property('intensity',.25)
post=spawn(u.PostProcessVolume,(0,0,100),label='Interior exposure')
post.set_editor_property('unbound',True)
settings=post.get_editor_property('settings')
settings.set_editor_property('override_auto_exposure_bias',True)
settings.set_editor_property('auto_exposure_bias',0.0)
settings.set_editor_property('override_auto_exposure_min_brightness',True)
settings.set_editor_property('override_auto_exposure_max_brightness',True)
settings.set_editor_property('auto_exposure_min_brightness',5.0)
settings.set_editor_property('auto_exposure_max_brightness',5.0)
post.set_editor_property('settings',settings)
# Player faces the desk and clock, with room to explore.
start=spawn(u.PlayerStart,(-180,-25,100),(0,-14,0),'First person start')
world=levels.get_current_level().get_outer() if False else u.EditorLevelLibrary.get_editor_world()
world.get_world_settings().set_editor_property('default_game_mode',mode.generated_class())
levels.save_current_level()
for asset in [door,player,hud,mode]:compile(asset)
u.EditorAssetLibrary.save_directory('/Game',only_if_is_dirty=False,recursive=True)
u.log('THE LAST ROOM BUILD COMPLETE')






