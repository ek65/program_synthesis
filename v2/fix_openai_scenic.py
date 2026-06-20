import json
from nlp_utils import Chat, client
from api_utils import API


def get_im(path):
    with open(path, "rb") as im:
        return im.read()



# Example script (hardcoded)
EX_SCRIPT = """
### Modeling Physical Conditions using APIs from the provided API library

# We call the conditions modeling the destination position of the coach as "target" APIs, and name these APIs with the prefix "target_" as shown below. 
A1target_0 = DistanceTo({'from': 'opponent', 'to': 'Coach', 'min': {'avg': 6.399477695297064, 'std': 0.8416729364595561}, 'max': None, 'operator': 'greater_than'})
A2target_0 = HorizontalRelation({'obj': 'Coach', 'ref': 'opponent', 'relation': 'left', 'horizontal_threshold': {'avg': 4.0, 'std': 1.0}})
A1target_2 = DistanceTo({'from': 'Coach', 'to': 'opponent', 'min': {'avg': 6.172259899611368, 'std': 0.0}, 'max': None, 'operator': 'greater_than'})
A2target_5 = DistanceTo({'from': 'Coach', 'to': 'goal', 'min': None, 'max': {'avg': 11.941602839093648, 'std': 0.01539784416917822}, 'operator': 'less_than'})

# We call the conditions modeling the preconditions of the coach as "precondition" APIs, and name these APIs with the prefix "precondition_" as shown below. 
A1precondition_0 = MakePass({'player': 'teammate'})
A1precondition_1 = Pressure({'player1': 'opponent', 'player2': 'Coach'})
A1precondition_3 = Pressure({'player1': 'opponent', 'player2': 'Coach'})
A1precondition_4 = MovingTowards({'obj': 'Teammate', 'ref': 'goal'})

def λ_target0():
    # the target APIs can be "composed" using conjunction (&), disjunction (|), or negation (~) operators.
    cond = A1target_0 & A2target_0
    # you should always return .dist() over either composed or singular target condition in the following format
    return cond.dist(simulation(), ego=True)

def λ_target2():
    return A1target_2.dist(simulation(), ego=True)

def λ_target5():
    return A2target_5.dist(simulation(), ego = True)

def λ_precondition_0():
    # for preconditions and termination conditions, you can also compose them using conjunction (&), disjunction (|), or negation (~) operators in the same way as target APIs.
    # you should always return .bool() over either composed or singular precondition in the following format
    return A1precondition_0.bool(simulation())

def λ_precondition3():
    # here is an example of calling a negation
    cond = ~ A1precondition_3
    return cond.bool(simulation())

def λ_precondition_1():
    return A1precondition_1.bool(simulation())

def λ_precondition_4():
    return A1precondition_4.bool(simulation())

behavior CoachBehavior(): 
    # You need to always start the coach behavior with the followin line, idling for 3 seconds.
    do Idle() for 3 seconds
    # The following structure defines a finite state machine (FSM), where each node is defined as "do <action> until <condition>"
    # and each transition edge is defined as "do Idle() until <condition>". For each node or edge, you need to preceed it with a speak line to explain what to do as below. 
    # Here we start with an action node. Also, when explaining any action nodes or transition edges, you should explain the numerical detail. 
    # Only report the average value (if defined) in the condition up the nearest integer. No need to report the standard deviation. 
    do Speak("you should move away from opponent by more than 6 meters by moving to the left, and recieve the ball from teammate")
    do MoveTo(λ_target0(), True)

    # Following the action node above, we have two transition edges branching out. 
    do Speak("wait to see if the opponent decides to pressure you or not")
    do Idle() until True # when branching occurs, always add this statement as a formality. 
    
    # Here we have a conditional branching. whenever we have conditional branching like this use if/elif/else conditions
    if λ_precondition_1(): # explain the precondition in the speak line below.
        # within each conditional branch, always first explain the condition that is just satisfied and then explain the action (node) that is about to be taken.
        do Speak("In this case, the opponent is pressuring you.")
        do Speak("So, move more than 6 meters away from opponent")
        do MoveTo(λ_target2(), False)

        # explain the transition edge below
        do Speak("wait until teammate moves towards goal")
        do Idle() until λ_precondition_4()

        # explain the action node below
        do Speak("pass the ball to teammate")
        do Pass(teammate)
    else:
        # again, for each conditional branch, explain the condition that is just satisfied and then explain the action (node) that is about to be taken.
        do Speak("The opponent is not pressuring you.")
        do Speak("Hence, move close to goal, within 12 meters")
        do MoveTo(λ_target5())

        # in case when there is no condition for transition edge, then you can just omit Speak() and do Idle() until ... line and move straight to the action node below.
        do Speak("then take a shot towards the goal")
        do Shoot(goal)
    
    # the coach behavior must always end with an idle state as below. 
    do Idle()

"""
    
class Fix_OpenAI_Scenic:
    """
    Fixes a Scenic program using instructor feedback and access to Scenic documentation.

    Args:
        scenic_code (str): The original Scenic code to be fixed.
        feedback (str): Instructor feedback on what needs to change.
        scenic_docs_url (str): URL to Scenic language/API documentation.
    """

    def __init__(self, scenic_code: str, feedback: str, scenic_docs_url: str, api, context: str, synth_demo, demos, use_synth_demo: bool = True, fsm: bool = False, model: str = "gpt-5-mini"):
        self.scenic_code = scenic_code
        self.feedback = feedback
        self.scenic_docs_url = scenic_docs_url
        self.api = api
        self.constraintAPI = api[API.constraints]
        self.actionAPI = api[API.actions]
        self.context = context
        self.synth_demo = synth_demo
        self.demos = demos
        self.use_synth_demo = use_synth_demo
        self.fsm = fsm
        self.model = model
        # print(self.constraintAPI)
        # print(self.actionAPI)
# - 'Coach Feedback': A text narration pointing out the issue with the coach behavior.
    def build_prompt(self) -> str:
        # Check if original demos are provided
        has_original_demos = self.demos is not None and len(self.demos) > 0
        all_objects = {f"{obj.label}" for demo in self.demos for obj in demo.scene.objects}

#         original_demos_section = ""
#         if has_original_demos:
#             original_demos_section = """
# - 'Original Narrated Demonstrations': This contains a set of videos and corresponding transcripts of narrated demonstrations from the coach that is previously used to model the CoachBehavior() in the program.
#         These transcripts consists only of what the coach said, and videos showing the coach performing the task.
# """
#         else:
#             original_demos_section = """ """

        # FSM related se
        fsm_related_section = """
        In this setting, the coach is shown the finite state machine (FSM) structure of the CoachBehavior() function and provides feedback on how to fix the coach behavior. 
        Through our editing interface, the coach can annotate on the FSM (by clicking edges or nodes) to indicate where in the program to fix. 
        The feedback is provided as a transcript which contains the narration of the coach's feedback and annotations of the node(s) and the edge(s) that the coach clicked on the FSM.
        The annotations of which edges or nodes are clicked are embedded in the transcript to preserve the temporal order of the feedback so that you can associate 
        different feedback with different nodes and edges that are clicked. In particular, the annotations are specified within square brackets [] in the transcript.
        
        For context, the CoachBehavior() code structure reflects a FSM, where:
        - Nodes are represented as: "do actionAPI until termination_condition" 
        - Edges are represented as: "do Idle() until precondition" (constraintAPI)
        - the termination and pre-conditions are modeled using the provided APIs on modeling constraints 
        - The FSM has a virtual start node, which is the first node in the FSM, which represents : "do Idle() for 3 seconds" at the beginning of the CoachBehavior() function.
        - There is one or more virtual edge(s) from the start node to the first node in the FSM.

        For context, regarding the structure of the annotations, 
        If there is no conditional (if/elif/else) statement immediately following "do Idle() for 3 seconds" at the beginning of CoachBehavior(), then there will be only only virtual edge; \
        otherwise, there will be multiple virtual edges. An example of a single virtual edge (with no conditional) is: "[User annotated edge 1001 with description [Transition 1001] Initial Transition.]".
        As you can see, the description of the annotated edge or node is embedded in the square brackets, always starting with "[User annotated edge" or "[User annotated node".
        In this case, specifically for no conditional, the description is "[Transition 1001] Initial Transition". 
        Otherwise, the verbatim description of corresponding SpeakAction() in the CoachBehavior() will be embedded in the square brackets.

        The annotations contain descriptions of either nodes or edges, which are equivalent in verbatim to the descriptions specified in the SpeakAction() in the CoachBehavior().
        These annotations should help you easily debug where in the code to fix. In particular, by comparing the annotations and the texts within SpeakAction() in the CoachBehavior(),\
        you should be able to identify what's coach's feedback and to which line of the program the coach is providing the feedback.
        """

        system_execution_feedback_section = """
        In this setting, the coach observes the program's execution (where the coach behavior controls an agent in the simulation) in simulation and provides feedback on how to fix the coach behavior. 
        You are given (1) the video of the program's execution and (2) the transcript of the coach's feedback. In the video, coach may annotate on the field using X marks when giving feedback on positioning.

        The transcript contains coach's feedback on how to fix the coach behavior as well as annotations of the X marks on the field. 
        This annotation is embedded in the transcript to preserve the temporal order of the feedback so that you can associate each annotation with the corresponding feedback.
        The annotation is specified within square brackets [] in the transcript always starting with "[Coach points to ..."].
        Potentially, coach may provide multiple feedback throughout the video/transcript with multiple corresponding X mark annotations. 
        Your task is to identify the feedback with the corresponding X mark annotations, and then fix the code accordingly.

        The transcript also contains narration provided by the CoachBehavior() -- the narrations are specified within the SpeakAction() in the CoachBehavior().
        As coach observes the program's execution, the narration is provided by the SpeakAction() in the CoachBehavior() to explain the coach's behavior.
        The coach can provide feedback by pausing in between these narrations from the program.
        When reading the transcript, you will need to differentiate between the coach's feedback and the narration from the program. \
        This should be easy because the speak action is acting like a debug print statements that you can reference to debug the program. 
        In particular, by comparing the transcript and the texts within Speak actions in the program, you should be able to identify what's coach's feedback and to which line of the program the coach is providing the feedback.
        Coach may provide multiple feedback throughout the video/transcript. Your task is identify the feedback on the coach behavior and the lines of code to fix, and then actually fix accordingly.
        """

        additional_inputs = """
        - 'Original Narrated Demonstrations': This contains a set of videos and corresponding transcripts of narrated demonstrations from the coach that is previously used to model the CoachBehavior() in the program.
            The 'Scenic Code Snippet' that you are reviewing right now is supposed to model the coach's behavior. If not, then coach will provide feedback that is consistent with the original demonstrations.
            Please reference this information to understand the coach's feedback in order to fix the code as coach intended. 
            You are given the videos of the original demonstrations in videos, and the transcripts of the narrations in the videos. 
            The videos and transcripts are indexed to indicate which video corresponds to which transcript. 
            Each video is given as a sequence of image frames. 
        """

        return f"""
        You are a helpful coding assistant. Your task is to help fix a program written in Scenic programming language based on a feedback.
        The Scenic is a domain-specific language embedded in Python for modeling and simulating physical scenarios in simulation.
        So, it inherits the syntax and semantics of Python. 

        We have a program that models a behavior of a soccer coach. 
        In this setting the coach is providing you with feedback on how to fix the coach behavior. 

        You are given:
        - 'Scenic Code Snippet': This is the part of the full Scenic code, which models the coach behavior, and is the part that needs to be fixed based on the coach's feedback.
        You should only modify this code snippet, and leave the rest of the code intact.
        - 'Full Scenic program' which models a soccer scenario with agents and their behaviors, including the scenic code snippet. This is provided for your context in fixing the coach behavior. 
        - 'Scenic Documentation': This is a documentation regarding Scenic syntax and semantics: {self.scenic_docs_url}
        - 'Actions and Constraint APIs': A library of APIs for defining action space and constraints to model coach behavior. Do not create or reference new APIs, only use the ones in this library to model the coach's behavior.
        - 'Feedback on how to fix the coach behavior': This is the feedback from the coach on how to fix the coach behavior. 
        - 'Example Scenic program': An example Scenic program for you to reference the structure of the code to maintain in your fixed code. 
        {(additional_inputs if self.fsm else "")} 

        {(fsm_related_section if self.fsm else system_execution_feedback_section)} 

        Your task is to fix only the CoachBehavior() and the lambda functions it uses (with the constraints) to address the instructor's feedback.

        *** Constraints to Enforce in Fixing the Code:
        - *IMPORTANT* If coach asks you to modify the constraints, make sure to check that you are modifying each corresponding constraint *CONSISTENTLY throughout* the code. 
           For example, if you deleted a constraint, then make sure that constraint name is not referenced throughout the code. Otherwise, the code will run into compilation error. 
        - *IMPORTANT* After you modify the constraints, make sure to update the explanation in the Speak() accordingly following the format of the code structure guideline below and the example Scenic program.
        - Only change what is needed to resolve the issues raised and preserve the original structure and logic as much as possible. 
        - Use valid Scenic syntax and semantics — check the documentation if needed.
        - Only use valid constraints and actions as specified in APIs. Do *not* create or reference new APIs that are not in the APIs library. 
        - Do not add unrelated objects or behaviors.
        - Provide annotations *in the code* explaining what was changed and why.
        - Do not import anything. Assume that all the provided APIs are imported in the file. 
          And, your output will be copied and pasted into the existing Scenic file which already has instantiated objects and players.
        - Make sure that 'CoachBehavior()' starts with 'do Idle() for 3 seconds' and ends with 'do Idle()'
        - Each action should be preceded by a correct precondition: either 'do Idle() until precondition', or if we have multiple preconditions leading to different actions we should \
            have if/elif/else structure.
        - Unless otherwise stated that a parameter is optional, it *must* be filled out.

        *** Guidelines on the Structure of the Code to Maintain: Please reference the example Scenic program for the structure of the code.
        Note that the program you are fixing is written in the format explained in this guideline. Maintain this format as you fix the code. 
        - Write a Scenic behavior called `behavior CoachBehavior():' along with constraint definitions outside the CoachBehavior() function.
        - The program should be structured in the same format as in the provided example Scenic program. 
        - The program structure represents a finite state machine (FSM):
            For context, the CoachBehavior() code structure should reflects a FSM, where:
                - Nodes are represented as: "do actionAPI until termination_condition" 
                - Edges are represented as: "do Idle() until precondition" (constraintAPI)
                - the termination and pre-conditions are modeled using the provided APIs on modeling constraints 
        - A 'do Speak("...")' line before each action and precondition (max 20 words) for a soccer coach:
                a) These 'do Speak("...")' have to describe the action or precondtion in plain English in the same style as shown in the example Scenic program. 
                b) We will execute the CoachBehavior() to have your modeled behavior narrate and demonstrate back what it learned. 
                Watching and listening to your code's execution, we will have the expert to give corrective feedback. 
                So, make sure that your speak action contains sufficient information about the code logic but in plain laymen's term such that
                experts without programming background can easily correct the code. 
                When possible you should use action's or precondition's input values that are important. 
        - All necessary constraint class instantiations, these should be instantiated *outside* the 'behavior CoachBehavior():' block
        - All λ_target, λ_termination, and λ_precondition functions, each defined explicitly, these should be instantiated *outside* the 'behavior CoachBehavior():' block
        - These are the names of the instantiated objects and players. Only use these objects' and players' names to reference objects (don't declare new object or player names): {', '.join(sorted(all_objects))}
        - When invoking APIs, make sure to reference objects or players by their names in "string" format as indicated in the API documentation. Do not use the objects directly. 
        - Make sure you abide by the API documentation's input argument types and formats. 
        - The CoachBehavior() function and the constraint definitions should be the only functions and constraints in the file. 
        - Unless otherwise stated that a parameter is optional, all the parameters of the APIs you invoke *must* be filled out in the correct type/format as defined in the API documentation.
        - Please always start 'CoachBehavior():' block with do Idle() for 3 seconds, and end the function with do Idle() as shown in the example Scenic program.
        - The λ_termination function must not represent the goal or intended outcome of the action itself.
        For example, if the action is MoveTo(...) and the goal is to obtain a clear passing path, then λ_termination = HasPath(...).bool is invalid—because HasPath is the desired result of moving.
        Instead, termination should be triggered by an intermediate signal or condition indicating when the action should stop (e.g., a change in environment), not the success condition of the action.
        - Each action (except the first one and possibly THE FIRST ACTION AFTER THE FIRST do Speak line) should be preceded by a correct precondition: either 'do Idle() until precondition', or if we have multiple preconditions leading to different actions we should have if/elif/else structure as shown in the example Scenic program.
            a) IMPORTANT: Whenever you define a constraint, make sure it is possible to fulfill — especially constraints involving ball possession at the beginning of the scenario. For this reason, the first action after the first do Speak("...") line does not need a precondition.
            b) In case you create if/else structure, you can use if/elif/else. DO NOT USE else if, that would error!
            c) When using if/elif/else conditions, use 'do Speak("...")' to explain which condition is satisfied first, and then 
            in the immediate next line add another do Speak("...")' to explain the action that is to be taken in the following line as shown in the example Scenic program.

        *** You should output in the following format:
        1. First explain briefly:
        - The summary of the feedback. 
        - What exactly you changed in the Scenic code.
        2. Then output only the CoachBehavior() *and* supporting lambda functions and constraints. Do not output the rest of the code.
        - Do *not* provide header like ```python or ```scenic. Only output the code so that it can be directly copied and pasted to another template program. 
        - Don't rearange code, unless that's the fix. If you keep some parts they should be in the same place. 
        - ABSOLUTELY MAKE SURE TO OUTPUT THE CODE YOU DIDNT CHANGE AS WELL. FOR EXAMPLE, LAMBDA FUNCTIONS AND CONSTRAINTS YOU DID NOT CHANGE SHOULD BE OUTPUTTED AS WELL.
            This is to ensure that all the of the lambdas have conditions that are defined.

        """.strip()

    def run(self):
        chat = Chat(client, model=self.model)
        print(f"Fixing Scenic program with OpenAI model: {self.model}")
        messages = [
            Chat.Entry("system", self.build_prompt()),
            Chat.Entry("user", f"Snippet of the Scenic program that you need to fix:\n{self.scenic_code}"),
            Chat.Entry("user", f"Full scenic program provided for context:\n{self.context}"),
            # Chat.Entry("user", f"Instructor Feedback:\n{self.feedback}"),
            Chat.Entry(role='system', text='Library of actionAPIs:\n\n' + '\n\n'.join([f'[API ID] {i}\n{c.doc()}' for i, c in self.actionAPI.items()])),
            Chat.Entry(role='system', text='Library of constraintAPIs:\n\n' + '\n\n'.join([f'[API ID] {i}\n{c.doc()}' for i, c in self.constraintAPI.items()]))
            # Chat.Entry(role='user', text="Transcripts from the original narrated demonstrations:\n" + "\n---\n".join(demo.language for demo in self.demos)),
            # Chat.Entry(role='user', text="Transcript(s) from the video(s) that the coach provided feedback for:\n" + "\n---\n".join(self.synth_demo.language)),
        ]

        # Add example Scenic program
        messages.append(Chat.Entry(role='user', text="Example Scenic program:\n" + EX_SCRIPT))

        # Add original demonstrations if available
        if self.demos is not None and len(self.demos) > 0:
        
            messages.extend(
                Chat.Entry(role='user', text=f"Transcript {demo.id} (these indicies match the indicies of the lists of videos that are given later, e.g. transcript 1 is for video 1):\n{demo.language}")
                for i, demo in enumerate(self.demos)
            )

            for demo in self.demos:
                for idx, frame_path in enumerate(demo.video.frame_dir):
                    messages.append(
                        Chat.Entry(role='user', text=f"Video {demo.id} - Frame {idx}", im=get_im(frame_path))
                    )

        if self.use_synth_demo:
            synth_demos = getattr(self, 'synth_demo', [])
            if not isinstance(synth_demos, list):
                synth_demos = [synth_demos] if synth_demos else []

            for i, demo in enumerate(synth_demos):
                if self.fsm:
                    # When fsm is True, use language from use_synth_demo as feedback
                    messages.append(
                        Chat.Entry(
                            role='user',
                            text=(
                                f"Coach Feedback about the FSM: The FSM (Finite State Machine) represents the code structure in the CoachBehavior() function. Here is the coach's feedback about the FSM that you need to implement in the code:\n{demo.language}"
                            )
                        )
                    )
                else:
                    # Original behavior
                    messages.append(
                        Chat.Entry(
                            role='user',
                            text=(
                                f"Transcript of the coach's feedback which contains the information you want to fix in code: \n{demo.language}"
                            )
                        )
                    )

            if not self.fsm:
                for demo in synth_demos:
                    if hasattr(demo, 'video') and demo.video:
                        for idx, frame_path in enumerate(demo.video.frame_dir):
                            messages.append(
                                Chat.Entry(role='user', text=f"Video of Feedback - image frame index: {idx}", im=get_im(frame_path))
                            )

        response = chat(messages)
        # print("RESPONSE: ", response)
        fixed_code = self.extract_code(response)
        # print("FIXED CODE: ", fixed_code)
        return fixed_code, response

    def extract_code(self, text: str) -> str:
        """Extract Scenic code block from model response."""
        try:
            # Find first triple backtick block for code
            start = text.index("```")
            end = text.index("```", start + 3)
            return text[start+3:end].strip()
        except ValueError:
            return text.strip() 